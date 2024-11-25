#!/bin/sh

# Start up django webserver
./manage.py migrate
./manage.py collectstatic --noinput

# Classic Django devserver
#./manage.py runserver 0.0.0.0:5173

# Uvicorn devserver (preferred)
uv run uvicorn thunderbird_accounts.asgi:application --reload  --host 0.0.0.0 --port 5173 --reload-include *.html