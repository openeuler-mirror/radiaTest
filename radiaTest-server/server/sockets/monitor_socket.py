from flask_socketio import Namespace
import json
from threading import Lock
import abc

from server import socketio

class MonitorSocket(Namespace):
    def __init__(self, namespace) -> None:
        super().__init__(namespace)
        self.monitors_lock = Lock()
    
    @abc.abstractmethod
    def on_connect(self):
        pass

    @abc.abstractmethod
    def on_start(self):
        pass
    
    @abc.abstractmethod
    def on_end(self):
        pass
    
    @abc.abstractmethod
    def on_disconnect(self):
        pass


class LocalMonitorSocket(MonitorSocket):
    def __init__(self, namespace, Monitor) -> None:
        super().__init__(namespace)
        self.monitor = Monitor(namespace)

    def on_connect(self):
        with self.monitors_lock:
            self.monitor.watcher_num += 1
            if not self.monitor.thread:
                self.monitor.thread = socketio.start_background_task(
                    target=self.monitor.run
                )

    def on_start(self):
        pass

    def on_end(self):
        pass

    def on_disconnect(self):
        with self.monitors_lock:
            self.monitor.watcher_num -= 1


class RemoteMonitorSocket(MonitorSocket):
    def __init__(self, namespace, Monitor) -> None:
        super().__init__(namespace)
        self.Monitor = Monitor
        self.namespace = namespace
        self.monitors = dict()
    
    def on_connect(self):
        pass

    def on_start(self, ssh_data):
        with self.monitors_lock:
            if not self.monitors.get(ssh_data["ip"]):
                self.monitors[ssh_data["ip"]]= self.Monitor(
                    self.namespace, ssh_data
                )

            self.monitors[ssh_data["ip"]].watcher_num += 1
            if not self.monitors[ssh_data["ip"]].thread:
                self.monitors[ssh_data["ip"]].thread = socketio.start_background_task(
                    target=self.monitors[ssh_data["ip"]].run
                )
    
    def on_end(self, ip):
        with self.monitors_lock:
            if self.monitors.get(ip):
                self.monitors[ip].watcher_num -= 1
                if self.monitors[ip].watcher_num == 0:
                    del self.monitors[ip]

    def on_disconnect(self):
        pass

