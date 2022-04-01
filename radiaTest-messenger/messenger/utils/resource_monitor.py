import requests
import json
import time
import abc

from messenger import socketio
from messenger.utils.pssh import Connection
from messenger.utils.common_cli import CommonCli


class ResourceMonitor:
    def __init__(self, namespace) -> None:
        self.watcher_num = 0
        self.namespace = namespace
        self.thread = None
        self.event = "response"

    @abc.abstractmethod
    def get_data(self):
        pass
    
    def run(self):
        while self.watcher_num > 0:

            resp = self.get_data()

            socketio.emit(
                self.event, 
                resp, 
                namespace=self.namespace
            )

            time.sleep(1)


class RemoteShellMonitor(ResourceMonitor):
    def __init__(self, namespace, ssh_data) -> None:
        super().__init__(namespace)
        self.group_ip = ssh_data["machine_group_ip"]
        self.ip = ssh_data["machine_ip"]
        self.user = ssh_data["user"]
        self.port = int(ssh_data["port"])
        self.password = ssh_data["password"]
        self.event = ssh_data["ip"]
        self.ssh_client = None
    
    def run(self):
        while self.watcher_num >= 0:
            if self.watcher_num == 0:
                if self.ssh_client:
                    self.ssh_client._close()
                break

            if not self.ssh_client:
                is_conn = self._connect()
                if is_conn:
                    resp = self.get_data()
                    socketio.emit(self.event, resp, namespace=self.namespace)

            time.sleep(1)

    def _connect(self):
        self.ssh_client = Connection(
            self.ip, 
            self.password, 
            self.port, 
            self.user
        )
        return self.ssh_client._conn()

    def get_data(self):
        mem_total = self.ssh_client._command(CommonCli.mem_total_cli)[1]
        mem_usage = self.ssh_client._command(CommonCli.mem_usage_cli)[1]
        cpu_usage = self.ssh_client._command(CommonCli.cpu_usage_cli)[1]
        cpu_index = self.ssh_client._command(CommonCli.cpu_index_cli)[1]
        cpu_num = self.ssh_client._command(CommonCli.cpu_num_cli)[1]
        cpu_physical_cores = self.ssh_client._command(CommonCli.cpu_physical_cores_cli)[1]
        cpu_logical_cores = self.ssh_client._command(CommonCli.cpu_logical_cores_cli)[1]
        os_info = self.ssh_client._command(CommonCli.os_cli)[1]
        kernel_info = self.ssh_client._command(CommonCli.kernel_cli)[1]

        cpu_physical_cores_real = 'unknown'
        if type(cpu_physical_cores) == int and type(cpu_num) == int:
            cpu_physical_cores_real = int(cpu_physical_cores) * int(cpu_num)

        return {
            "machine_group_ip": self.group_ip,
            "machine_ip": self.ip,
            "cpu_usage": float(cpu_usage.strip()),
            "mem_usage": float(mem_usage.strip()),
            "mem_total": float(mem_total.strip()),
            "cpu_index": cpu_index,
            "cpu_physical_cores": cpu_physical_cores_real,
            "cpu_logical_cores": int(cpu_logical_cores),
            "os_info": os_info.strip(),
            "kernel_info": kernel_info.strip(),
        }
            

class RemoteRestfulMonitor(ResourceMonitor):
    def __init__(self, namespace, ssh_data) -> None:
        super().__init__(namespace)
        self.ssh_data = ssh_data
    
    def get_data(self):
        resp = requests.get(
            url='http://{}:{}/monitor'.format(
                self.ssh_data["ip"], 
                self.ssh_data["listen"]
            ),
            headers={"Content-Type": "application/json;charset=utf8"}
        )
        resp.encoding = resp.apparent_encoding

        if resp.status_code != 200:
            return {}
        else:
            data = json.loads(resp.text)

            return {
                "machine_group_ip": self.ssh_data.get("machine_group_ip"),
                "machine_ip": self.ssh_data.get("machine_ip"),
                **data
            }
