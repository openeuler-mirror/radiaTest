#! /bin/sh

if python3 manage.py db migrate; then
    python3 manage.py db upgrade || exit
else
    python3 manage.py db init || exit \
        && python3 manage.py db migrate || exit \
        && python3 manage.py db upgrade || exit
fi

