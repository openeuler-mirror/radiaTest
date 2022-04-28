#! /bin/sh

if [ ! -d "./migrations" & ! -f "./migrations/env.py" ];then
    python3 manage.py db init || exit 
fi

python3 manage.py db migrate || exit \
    && python3 manage.py db upgrade || exit