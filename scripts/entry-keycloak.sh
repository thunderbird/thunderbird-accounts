#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOOTSTRAP_HTTP_PORT="${KC_BOOTSTRAP_HTTP_PORT:-18080}"
BOOTSTRAP_MANAGEMENT_PORT="${KC_BOOTSTRAP_HTTP_MANAGEMENT_PORT:-19000}"

stop_bootstrap() {
    kill -TERM "$KC_PID" 2>/dev/null || true
    wait "$KC_PID" 2>/dev/null || true
}

# Bootstrap on internal-only ports so the load balancer cannot route to this task until
# reconciliation and its integrity check succeed.
if [[ "${KC_DEV:-}" == 'yes' ]]; then
    KC_HTTP_PORT="$BOOTSTRAP_HTTP_PORT" \
    KC_HTTP_MANAGEMENT_PORT="$BOOTSTRAP_MANAGEMENT_PORT" \
        /bin/bash /opt/keycloak/bin/kc.sh start-dev --import-realm &
else
    KC_HTTP_PORT="$BOOTSTRAP_HTTP_PORT" \
    KC_HTTP_MANAGEMENT_PORT="$BOOTSTRAP_MANAGEMENT_PORT" \
        /bin/bash /opt/keycloak/bin/kc.sh start --http-enabled=true --proxy-headers forwarded &
fi
KC_PID=$!
trap stop_bootstrap TERM INT

if ! KC_HTTP_PORT="$BOOTSTRAP_HTTP_PORT" \
    KC_HTTP_MANAGEMENT_PORT="$BOOTSTRAP_MANAGEMENT_PORT" \
    KEYCLOAK_BOOTSTRAP_PID="$KC_PID" \
    /bin/bash "$SCRIPT_DIR/apply-mfa-config.sh"; then
    stop_bootstrap
    exit 1
fi

stop_bootstrap
trap - TERM INT

if [[ "${KC_DEV:-}" == 'yes' ]]; then
    exec /bin/bash /opt/keycloak/bin/kc.sh start-dev --import-realm
fi

exec /bin/bash /opt/keycloak/bin/kc.sh start --http-enabled=true --proxy-headers forwarded
