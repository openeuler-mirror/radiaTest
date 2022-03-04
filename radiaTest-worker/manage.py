from gevent import monkey, pywsgi

monkey.patch_all()

from flask_script import Manager

from worker import create_app
from worker.plugins.monitor import IllegalMonitor
from worker.utils.daemon import DaemonThread


app = create_app()

manager = Manager(app)


@manager.command
def run_gevent():

    # DaemonThread(IllegalMonitor(app, 600)).start()

    server = pywsgi.WSGIServer(
        (app.config.get("WORKER_IP"), app.config.get("WORKER_PORT")), app
    )
    server.serve_forever()


if __name__ == "__main__":
    manager.run()
