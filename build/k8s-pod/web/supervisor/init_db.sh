#! /bin/sh

if [[ ! -d "./migrations" || ! -f "./migrations/env.py" || ! -f "./migrations/alembic.ini" || ! -d "./migrations/version" ]];then
    rm -rf ./migrations/* \
        && python3 manage.py db init || exit 
fi

python3 manage.py db migrate

python3 manage.py db upgrade