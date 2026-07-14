#!/bin/bash

echo 'Removing build and module source autogen files...'

rm -rf build
rm -rf docs/thunderbird_accounts

echo 'Building documentation!'

uv run sphinx-build docs build

echo 'Running python server on http://localhost:8000'

cd build && python -m http.server
