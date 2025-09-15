#!/bin/bash

# Usage:
#   Running this script with the default options will launch the backend in an environment-ready
#   mode. To run in development mode instead, run with KC_DEV=yes.

# Run the app with the appropriate command
if [[ "$KC_DEV" == "yes" ]]; then
    CMD="/bin/bash /opt/keycloak/bin/kc.sh start-dev --import-realm"
else
    CMD="/bin/bash /opt/keycloak/bin/kc.sh start --http-enabled=true --proxy-headers forwarded"
fi

$CMD
