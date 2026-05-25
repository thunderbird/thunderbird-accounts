#!/bin/bash

echo '----------------------  TEST  ----------------------'
sudo docker compose exec accounts uv run coverage run manage.py test $1

echo '---------------------- REPORT ----------------------'
sudo docker compose exec accounts uv run coverage report

echo '----------------------  HTML  ----------------------'
sudo docker compose exec accounts uv run coverage html

