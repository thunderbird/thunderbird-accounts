#!/bin/bash
#
# Reconcile the tbpro realm's remember-me settings and MFA step-up flow with
# keycloak-config-cli.
#
# Every replica waits for its local bootstrap server, then serializes through a database
# transaction lock. Config CLI's shared checksum cache makes later replicas skip the import.

set -euo pipefail

CONFIG_FILE='/opt/keycloak/config-cli/tbpro-mfa-stepup.yaml'
CONFIG_CLI_JAR='/opt/keycloak/keycloak-config-cli.jar'
HEALTH_PORT="${KC_HTTP_MANAGEMENT_PORT:-9000}"
HTTP_PORT="${KC_HTTP_PORT:-8080}"

kc_ready() {
    exec 3<>"/dev/tcp/localhost/${HEALTH_PORT}" || return 1
    printf 'GET /health/ready HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n' >&3
    local status_line
    IFS= read -r status_line <&3
    exec 3>&- 3<&-
    [[ "$status_line" == *" 200 "* ]]
} 2>/dev/null

login_flow_ready() {
    local client_id='thunderbird-accounts'
    if [[ "${KC_DEV:-}" == 'yes' ]]; then
        client_id='tb-accounts'
    fi

    local callback_url="${KC_TBPRO_HOME%/}/oidc/callback/"
    local encoded_callback="${callback_url//%/%25}"
    encoded_callback="${encoded_callback//:/%3A}"
    encoded_callback="${encoded_callback//\//%2F}"

    local scheme='http'
    if [[ "$KC_HOSTNAME" == https://* ]]; then
        scheme='https'
    fi
    local hostname="${KC_HOSTNAME#*://}"
    hostname="${hostname%%/*}"
    local request_path="/realms/tbpro/protocol/openid-connect/auth/?response_type=code&scope=openid%20email&client_id=${client_id}&redirect_uri=${encoded_callback}&state=integrity-check&nonce=integrity-check"

    exec 4<>"/dev/tcp/localhost/${HTTP_PORT}" || return 1
    printf 'GET %s HTTP/1.0\r\nHost: %s\r\nX-Forwarded-Host: %s\r\nX-Forwarded-Proto: %s\r\nConnection: close\r\n\r\n' \
        "$request_path" "$hostname" "$hostname" "$scheme" >&4
    local status_line
    IFS= read -r status_line <&4
    local response_body
    response_body=$(cat <&4)
    exec 4>&- 4<&-

    [[ "$status_line" == *" 200 "* && "$response_body" == *'data-page-id="login-login"'* ]]
}

for i in $(seq 1 300); do
    kc_ready && break
    if [[ -n "${KEYCLOAK_BOOTSTRAP_PID:-}" ]] && ! kill -0 "$KEYCLOAK_BOOTSTRAP_PID" 2>/dev/null; then
        echo 'apply-mfa-config: Keycloak bootstrap process exited before becoming ready.' >&2
        exit 1
    fi
    sleep 2
done
if ! kc_ready; then
    echo 'apply-mfa-config: Keycloak did not become ready within 10 minutes.' >&2
    exit 1
fi
echo "apply-mfa-config: Keycloak ready after ~$((i * 2))s; reconciling."

if [[ -z "${KEYCLOAK_ADMIN_CLIENT_SECRET:-}" ]]; then
    echo 'apply-mfa-config: KEYCLOAK_ADMIN_CLIENT_SECRET is required.' >&2
    exit 1
fi
if [[ -z "${KEYCLOAK_CONFIG_REVISION:-}" ]]; then
    echo 'apply-mfa-config: KEYCLOAK_CONFIG_REVISION is required.' >&2
    exit 1
fi

export KEYCLOAK_URL="http://localhost:${HTTP_PORT}"
export KEYCLOAK_REALM=master
export KEYCLOAK_GRANTTYPE=client_credentials
export KEYCLOAK_CLIENTID="${KEYCLOAK_ADMIN_CLIENT_ID:-tb-accounts-admin}"
export KEYCLOAK_CLIENTSECRET="${KEYCLOAK_ADMIN_CLIENT_SECRET}"
export IMPORT_FILES_LOCATIONS="${CONFIG_FILE}"
export IMPORT_VARSUBSTITUTION_ENABLED=true
export IMPORT_MANAGED_AUTHENTICATIONFLOW=no-delete
export IMPORT_MANAGED_CLIENT=no-delete
export IMPORT_CACHE_ENABLED=true
IMPORT_CACHE_KEY="image-$(printf '%s' "$KEYCLOAK_CONFIG_REVISION" | sha256sum | cut -d' ' -f1)"
export IMPORT_CACHE_KEY
export MFA_L1_LOA_MAX_AGE="${MFA_L1_LOA_MAX_AGE:-7776000}"
case "${TBPRO_MAIL_GATE:-}" in
    CONDITIONAL|DISABLED) ;;
    *)
        echo 'apply-mfa-config: TBPRO_MAIL_GATE must be CONDITIONAL or DISABLED.' >&2
        exit 1
        ;;
esac
export TBPRO_MAIL_GATE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JDBC_JARS=(/opt/keycloak/lib/lib/main/org.postgresql.postgresql-*.jar)

if [[ "${KEYCLOAK_CONFIG_LOCK_HELD:-}" != 'yes' ]]; then
    exec java -cp "${JDBC_JARS[0]}" "${SCRIPT_DIR}/PgAdvisoryLockRun.java" \
        env KEYCLOAK_CONFIG_LOCK_HELD=yes /bin/bash "$0"
fi

if [[ "${KEYCLOAK_CONFIG_CACHED:-}" == 'yes' ]]; then
    echo "apply-mfa-config: revision ${KEYCLOAK_CONFIG_REVISION} is already reconciled."
else
    java -jar "${CONFIG_CLI_JAR}"
fi

if ! login_flow_ready; then
    echo 'apply-mfa-config: login integrity check failed.' >&2
    exit 1
fi

echo 'apply-mfa-config: reconciliation and login integrity check passed.'
