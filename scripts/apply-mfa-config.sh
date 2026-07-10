#!/bin/bash
#
# Reconcile the tbpro realm's remember-me settings and MFA step-up flow with
# keycloak-config-cli.
#
# Runs in the background from entry-keycloak.sh on every Keycloak start (local + deploy):
# waits for the server to report ready, then applies keycloak/config-cli/tbpro-mfa-stepup.yaml
# declaratively. Fail-soft — it never blocks Keycloak from serving (a failed reconcile just
# logs and exits 0).

set -uo pipefail

CONFIG_FILE='/opt/keycloak/config-cli/tbpro-mfa-stepup.yaml'
CONFIG_CLI_JAR='/opt/keycloak/keycloak-config-cli.jar'
# Management interface (health/metrics) — enabled everywhere via KC_HEALTH_ENABLED=true.
HEALTH_PORT="${KC_HTTP_MANAGEMENT_PORT:-9000}"
# Keycloak's HTTP listener; differs by env (8999 local, 8080 deploy).
HTTP_PORT="${KC_HTTP_PORT:-8080}"

# Poll /health/ready over a raw bash TCP socket — the Keycloak image ships no curl/wget.
kc_ready() {
    exec 3<>"/dev/tcp/localhost/${HEALTH_PORT}" 2>/dev/null || return 1
    printf 'GET /health/ready HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n' >&3
    local status_line
    IFS= read -r status_line <&3
    exec 3>&- 3<&-
    [[ "$status_line" == *" 200 "* ]]
}

for _ in $(seq 1 90); do
    kc_ready && break
    sleep 2
done
if ! kc_ready; then
    echo 'apply-mfa-config: Keycloak did not become ready in time; skipping MFA flow reconcile.'
    exit 0
fi

if [[ -z "${KEYCLOAK_ADMIN_CLIENT_SECRET:-}" ]]; then
    echo 'apply-mfa-config: KEYCLOAK_ADMIN_CLIENT_SECRET unset; skipping MFA flow reconcile.'
    exit 0
fi

# config-cli authenticates as the same admin service-account client the accounts app uses.
# Override KEYCLOAK_URL via KC_CONFIG_CLI_URL if hostname-strict ever rejects localhost.
export KEYCLOAK_URL="${KC_CONFIG_CLI_URL:-http://localhost:${HTTP_PORT}}"
export KEYCLOAK_REALM=master
export KEYCLOAK_GRANTTYPE=client_credentials
export KEYCLOAK_CLIENTID="${KEYCLOAK_ADMIN_CLIENT_ID:-tb-accounts-admin}"
export KEYCLOAK_CLIENTSECRET="${KEYCLOAK_ADMIN_CLIENT_SECRET}"
export IMPORT_FILES_LOCATIONS="${CONFIG_FILE}"
export IMPORT_VARSUBSTITUTION_ENABLED=true
# Only ever add/overwrite the managed step-up flow; never delete other (built-in) flows.
export IMPORT_MANAGED_AUTHENTICATIONFLOW=no-delete
# Reconcile on every start, not just when the file changes: config-cli otherwise stores a
# file checksum on the realm and skips, so manual drift would never be repaired. Disabling
# the cache makes each start re-assert the flow. The reconcile is idempotent and adds ~1s
# to startup.
export IMPORT_CACHE_ENABLED=false
# Level-1 LoA window; must cover the realm's longest SSO session — the 90-day
# remember-me lifespan (see the config file).
export MFA_L1_LOA_MAX_AGE="${MFA_L1_LOA_MAX_AGE:-7776000}"

# Serialize the import across replicas with a Postgres advisory lock on Keycloak's own
# database: during a multi-replica deploy two containers run config-cli concurrently and
# the imports race — one fails mid-update ("Cannot remove authentication flow, it is
# currently in use") and leaves the flow half-updated, breaking browser logins. Advisory
# locks are session-scoped, so if a container dies mid-import the lock drops with its DB
# session and can never wedge a future deploy.
#
# PgAdvisoryLockRun.java takes the lock over the image's bundled Postgres JDBC driver
# (reading the same KC_DB_* vars Keycloak itself uses), holds it while running the
# command given in its argv, and is fail-soft: if the DB is unreachable it warns and
# runs the command without the lock. Run source-file style — no compile step needed.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Keycloak's bundled JDBC driver; the glob absorbs version bumps (java -cp itself only
# expands `dir/*`, so let the shell resolve it).
JDBC_JARS=(/opt/keycloak/lib/lib/main/org.postgresql.postgresql-*.jar)

java -cp "${JDBC_JARS[0]}" "${SCRIPT_DIR}/PgAdvisoryLockRun.java" \
    java -jar "${CONFIG_CLI_JAR}" \
    || echo 'apply-mfa-config: keycloak-config-cli failed (non-fatal).'
