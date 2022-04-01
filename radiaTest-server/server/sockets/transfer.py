import logging
from importlib_metadata import abc

from socketio import Client
from flask import request
from flask_socketio import Namespace

from server import socketio


logger = logging.getLogger(__name__)


def xterm_handler(data):
    ip = data.get("machine_ip")
    group_ip = data.get("machine_group_ip")
    if not ip or not group_ip:
        return

    socketio.emit(
        f"{ip}=>{group_ip}=>xterm",
        data,
        namespace="/xterm",
        broadcase=True,
    )

def normal_monitor_handler(data):
    ip = data.get("machine_ip")
    group_ip = data.get("machine_group_ip")
    if not ip or not group_ip:
        return

    socketio.emit(
        f"{ip}=>{group_ip}=>monitor",
        data,
        namespace="/monitor/normal",
        broadcast=True,
    )

def host_monitor_handler(data):
    ip = data.get("machine_ip")
    if not ip:
        return

    socketio.emit(
        f"{ip}=>monitor",
        data,
        namespace="/monitor/host",
        broadcast=True,
    )


class TransferSocket(Namespace):
    def __init__(self, namespace) -> None:
        super().__init__(namespace)
        self.sockets = dict()

    @abc.abstractmethod
    def register_on(self, group_ip, ip):
        pass

    def on_connect(self):
        query = request.args.to_dict()

        group_ip = query.get("machine_group_ip")
        if not group_ip:
            return
        
        if self.sockets.get(group_ip) is None:
            _socket = Client()

            self.sockets[group_ip] = {
                "socket": _socket,
                "connection_num": 0
            }
            
            self.sockets[group_ip]["socket"].connect(
                "http://{}:{}".format(
                    query.get("machine_group_ip"),
                    query.get("messenger_listen")
                ),
                namespaces=self.namespace,
            )
        
        self.sockets[group_ip]["connection_num"] += 1

        ip = query.get("machine_ip")
        if not ip:
            return

        self.register_on(group_ip, ip)
        

    def on_disconnect(self):
        query = request.args.to_dict()

        group_ip = query.get("machine_group_ip")
        if not group_ip:
            return
        
        self.sockets[group_ip]["connection_num"] -= 1
        if self.sockets[group_ip]["connection_num"] == 0:
            socket = self.sockets.pop(group_ip)
            socket["socket"].disconnect()


class XtermTransferSocket(TransferSocket):
    def register_on(self, group_ip, ip):
        if self.sockets[group_ip].get("socket"):
            self.sockets[group_ip]["socket"].on(
                ip,
                handler=xterm_handler,
                namespace=self.namespace,
            )

    def on_start(self, data):
        query = request.args.to_dict()

        group_ip = query.get("machine_group_ip")
        if not group_ip:
            return
        
        if self.sockets.get(group_ip):
            self.sockets[group_ip]["socket"].emit(
                "start",
                data={
                    **data,
                    "machine_group_ip": group_ip
                },
                namespace=self.namespace,
            )
    
    def on_command(self, data):
        query = request.args.to_dict()

        group_ip = query.get("machine_group_ip")
        if not group_ip:
            return
        
        if self.sockets.get(group_ip):
            self.sockets[group_ip]["socket"].emit(
                "command",
                data={
                    **data,
                    "machine_group_ip": group_ip
                },
                namespace=self.namespace,
            )

    def on_resize(self, data):
        query = request.args.to_dict()

        group_ip = query.get("machine_group_ip")
        if not group_ip:
            return
        
        if self.sockets.get(group_ip):
            self.sockets[group_ip]["socket"].emit(
                "resize",
                data={
                    **data,
                    "machine_group_ip": group_ip
                },
                namespace=self.namespace,
            )
    
    def on_end(self, data):
        query = request.args.to_dict()

        group_ip = query.get("machine_group_ip")
        if not group_ip:
            return
        
        if self.sockets.get(group_ip):
            self.sockets[group_ip]["socket"].emit(
                "end",
                data={
                    **data,
                    "machine_group_ip": group_ip
                },
                namespace=self.namespace,
            )


class NormalMonitorTransferSocket(TransferSocket):
    def register_on(self, group_ip, ip):
        if self.sockets[group_ip].get("socket"):
            self.sockets[group_ip]["socket"].on(
                ip,
                handler=normal_monitor_handler,
                namespace=self.namespace,
            )

    def on_start(self, data):
        query = request.args.to_dict()

        group_ip = query.get("machine_group_ip")
        if not group_ip:
            return
        
        if self.sockets.get(group_ip):
            self.sockets[group_ip]["socket"].emit(
                "start",
                data=data,
                namespace=self.namespace,
            )
    
    def on_end(self, data):
        query = request.args.to_dict()

        group_ip = query.get("machine_group_ip")
        if not group_ip:
            return
        
        if self.sockets.get(group_ip):
            self.sockets[group_ip]["socket"].emit(
                "end",
                data=data,
                namespace=self.namespace,
            )


class HostMonitorTransferSocket(NormalMonitorTransferSocket):
   def register_on(self, group_ip, ip):
        if self.sockets[group_ip].get("socket"):
            self.sockets[group_ip]["socket"].on(
                ip,
                handler=host_monitor_handler,
                namespace=self.namespace,
            )