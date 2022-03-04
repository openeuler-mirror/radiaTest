from gevent import monkey, pywsgi

monkey.patch_all()

from geventwebsocket.handler import WebSocketHandler
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from server.utils.celery_utils import make_celery
from server import create_app, db


my_celery = make_celery(__name__)

app = create_app(celery=my_celery)

manager = Manager(app)
migrate = Migrate(app, db)

manager.add_command("db", MigrateCommand)


@manager.command
def run_gevent():

    server = pywsgi.WSGIServer(
        (app.config.get("SERVER_IP"), int(app.config.get("SERVER_PORT"))),
        app,
        handler_class=WebSocketHandler,
    )
    server.serve_forever()


if __name__ == "__main__":
    manager.run()
