#!/bin/bash

echo '----------------------  TEST  ----------------------'
docker compose exec accounts uv run coverage run manage.py test $1

echo '---------------------- REPORT ----------------------'
docker compose exec accounts uv run coverage report

echo '----------------------  HTML  ----------------------'
docker compose exec accounts uv run coverage html

