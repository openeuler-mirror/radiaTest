from gevent import monkey, pywsgi

monkey.patch_all()

from geventwebsocket.handler import WebSocketHandler
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from server import create_app, db
from server.utils.daemon import DaemonThread
from server.plugins.monitor import LifecycleMonitor, RepoMonitor


app = create_app()

manager = Manager(app)
migrate = Migrate(app, db)

manager.add_command("db", MigrateCommand)


@manager.command
def run_gevent():

    DaemonThread(LifecycleMonitor(app, 300)).start()

    DaemonThread(RepoMonitor(app, 600)).start()

    server = pywsgi.WSGIServer(
        (app.config.get("SERVER_IP"), int(app.config.get("SERVER_PORT"))),
        app,
        handler_class=WebSocketHandler,
    )
    server.serve_forever()


if __name__ == "__main__":
    manager.run()
