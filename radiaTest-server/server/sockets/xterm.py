import logging
from threading import Thread

import paramiko
from gevent import sleep
from flask_socketio import Namespace
from paramiko.ssh_exception import NoValidConnectionsError, SSHException

from server import socketio


logger = logging.getLogger(__name__)


class ParamikoConsole:
    def __init__(self, machine_ip, port, user, password, cols, rows) -> None:
        self.machine_ip = machine_ip
        self.port = port
        self.user = user
        self.password = password
        self.pty_width = cols
        self.pty_height = rows

    @property
    def is_open(self):
        return self.ssh_channel.active
    
    def _pty_to_socket(self):
        try:
            while not self.ssh_channel.exit_status_ready():
                mesg = self.ssh_channel.recv(1024).decode("utf-8")
                if len(mesg) != 0:
                    socketio.emit(self.machine_ip, mesg, namespace="/xterm")
                else:
                    break
        except Exception as e:
            logger.error(str(e))
            socketio.emit(self.machine_ip, str(e), namespace="/xterm")
            self.close()

    def _socket_to_pty(self, cmd):
        try:
            self.ssh_channel.send(cmd)
        except OSError as e:
            logger.error(f"{str(e)}")
            socketio.emit(self.machine_ip, str(e), namespace="/xterm")
            self.close()

    def open(self):
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh_client.connect(
                hostname=self.machine_ip,
                username=self.user,
                port=self.port,
                password=self.password,
            )
        except (NoValidConnectionsError, SSHException) as e:
            logger.error(str(e))
            socketio.emit(
                self.machine_ip, 
                f"could not build SSH connection: {str(e)}", 
                namespace="/xterm"
            )
            return

        transport = ssh_client.get_transport()
        self.ssh_channel = transport.open_session()

        self.ssh_channel.get_pty(
            term="xterm",
            width=self.pty_width,
            height=self.pty_height,
        )
        self.ssh_channel.invoke_shell()

        self.ssh_channel.settimeout(None)
        sleep(1)

        mesg = self.ssh_channel.recv(2048).decode("utf-8")
        socketio.emit(self.machine_ip, mesg, namespace="/xterm")

    def close(self):
        try:
            self.ssh_channel.close()
            mesg = "SSH channel has been closed"
            logger.info(mesg)
        except BaseException as e:
            mesg = f"SSH channel could not be closed {str(e)}"
            logger.error(mesg)
        finally:
            socketio.emit(self.machine_ip, mesg, namespace="/xterm")

    def resize_pty(self, cols, rows):
        self.ssh_channel.resize_pty(width=cols, height=rows)

    def shell(self, cmd):
        Thread(target=self._socket_to_pty, args=(cmd,), daemon=True).start()
        Thread(target=self._pty_to_socket, daemon=True).start()


class TerminalSocket(Namespace):
    def __init__(self, namespace) -> None:
        super().__init__(namespace)
        self.machine_ip = ""
        self.port = 22
        self.user = "root"
        self.cols = 40
        self.rows = 80
        self.console = None

    def on_connect(self):
        logger.info(
            "socketio namespace /xterm has been connected"
        )

    def on_disconnect(self):
        if self.console is not None:
            self.console.close()
        
        logger.info(
            "socketio namespace /xterm has been disconnected"
        )

    def on_start(self, data):
        if data.get("machine_ip"):
            self.machine_ip = data.get("machine_ip")
        if data.get("port"):
            self.port = int(data.get("port"))
        if data.get("user"):
            self.user = data.get("user")
        if data.get("cols"):
            self.cols = int(data.get("cols"))
        if data.get("rows"):
            self.rows = int(data.get("rows"))

        self.console = ParamikoConsole(
            self.machine_ip,
            self.port,
            self.user,
            data.get("password"),
            self.cols,
            self.rows,
        )
        self.console.open()

    def on_command(self, data):
        if isinstance(self.console, ParamikoConsole) and self.console.is_open:
            self.console.shell(data.get("command"))

    def on_resize(self, data):
        if isinstance(self.console, ParamikoConsole) and self.console.is_open:
            self.console.resize_pty(data.get("cols"), data.get("rows"))