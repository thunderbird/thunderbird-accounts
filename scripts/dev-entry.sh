#!/bin/sh

# Wait until db is available
sleep 5s

# Start up django webserver
./manage.py migrate
./manage.py collectstatic --noinput

# Classic Django devserver
#./manage.py runserver 0.0.0.0:8087

# Uvicorn devserver (preferred)
uv run uvicorn thunderbird_accounts.asgi:application --reload  --host 0.0.0.0 --port 8087 --reload-include *.html
