#!/bin/bash

# Usage:
#   Running this script with the default options will launch the backend in an environment-ready
#   mode. To run in development mode instead, run with TBA_DEV=yes. To run the Celery worker
#   instead, run with TBA_CELERY=yes.

# In dev environments, give the DB a little extra time to come online
if [[ "$TBA_DEV" == "yes" ]]; then
    echo 'Waiting 1s for DB...'
    sleep 1s
fi

# Run the app with the appropriate command
if [[ "$TBA_CELERY" == "yes" ]]; then
    CMD="uv run celery -A thunderbird_accounts worker -l INFO"
else
    # Run migrations
    ./manage.py migrate

    # Retrieve paddle products & prices
    ./manage.py get_paddle_products
    ./manage.py get_paddle_prices

    CMD="uv run uvicorn thunderbird_accounts.asgi:application"
    ARGS="--lifespan off --host 0.0.0.0 --port 8087"
    if [[ "$TBA_DEV" == "yes" ]]; then
        ARGS="$ARGS --reload --reload-include *.html"
    fi
    CMD="$CMD $ARGS"
fi

$CMD
