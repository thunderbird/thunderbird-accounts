#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -eq 0 ]; then
  set -- thunderbird_accounts
fi

docker compose exec accounts uv run python manage.py test "$@"
