from gevent import monkey, pywsgi

monkey.patch_all()

from geventwebsocket.handler import WebSocketHandler
from flask_script import Manager
from flask_migrate import Migrate

from messenger.utils.celery_utils import make_celery
from messenger import create_app


my_celery = make_celery(__name__)

app = create_app(celery=my_celery)

manager = Manager(app)

@manager.command
def run_gevent():

    server = pywsgi.WSGIServer(
        (app.config.get("MESSENGER_IP"), int(app.config.get("MESSENGER_LISTEN"))),
        app,
        handler_class=WebSocketHandler,
    )
    server.serve_forever()


if __name__ == "__main__":
    manager.run()
