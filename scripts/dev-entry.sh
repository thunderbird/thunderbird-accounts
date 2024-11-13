#!/bin/sh

# Start up django webserver
./manage.py migrate
./manage.py runserver 0.0.0.0:5173
