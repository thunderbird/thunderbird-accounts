#!/bin/bash

#
# Run this before running local django tests otherwise your frontend view tests will fail!
#

npm run build
./manage.py collectstatic --noinput -i assets/app/vue
