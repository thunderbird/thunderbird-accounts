#!/bin/bash

# Usage:
#   Running this script with the default options will launch the backend in an environment-ready
#   mode. To run in development mode instead, run with KC_DEV=yes.

# Resolve our own location so we can invoke the sibling reconcile script regardless of the
# image's WORKDIR (the Keycloak base image runs with WORKDIR=/, so these scripts land at
# /scripts, not /opt/keycloak/scripts).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Start Keycloak in the background so we can reconcile the managed realm configuration once
# it's ready, then hand the foreground back to it. apply-mfa-config.sh runs
# keycloak-config-cli against the realm and is fail-soft.
if [[ "$KC_DEV" == "yes" ]]; then
    /bin/bash /opt/keycloak/bin/kc.sh start-dev --import-realm &
else
    # xforwarded, not forwarded: the load balancer in front of Keycloak terminates TLS and
    # forwards over plain HTTP with X-Forwarded-*. It never sends the RFC 7239 Forwarded
    # header, so `forwarded` left Keycloak treating every request as a non-secure context.
    # In that state it cannot emit SameSite=None (invalid without Secure) and falls back to
    # SameSite=Lax, which the browser then withholds on the cross-site POST back from the
    # MFA step -- surfacing as error="cookie_not_found" and a restarted login flow.
    # This is a CLI flag, so it also overrides KC_PROXY_HEADERS: setting that env var alone
    # cannot fix it.
    /bin/bash /opt/keycloak/bin/kc.sh start --http-enabled=true --proxy-headers xforwarded &
fi
KC_PID=$!

# Forward termination so container stop stays graceful.
trap 'kill -TERM "$KC_PID" 2>/dev/null' TERM INT

/bin/bash "$SCRIPT_DIR/apply-mfa-config.sh" &

wait "$KC_PID"
