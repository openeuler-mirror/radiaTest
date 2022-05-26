#! /bin/sh

python3 manage.py db init

python3 manage.py prepare_recv_id

python3 manage.py db migrate

python3 manage.py db upgrade

python3 manage.py init_asr