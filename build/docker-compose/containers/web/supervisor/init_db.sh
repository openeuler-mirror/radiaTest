#! /bin/sh

export FLASK_APP=/opt/radiaTest/radiaTest-server/manage.py

flask db init

flask db migrate

flask db upgrade

flask init_asr