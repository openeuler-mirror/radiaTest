import subprocess
import paramiko
import time
import abc
from paramiko.ssh_exception import NoValidConnectionsError, SSHException
import psutil

from worker import socketio
from worker.utils.common_cli import CommonCli


class ResourceMonitor:
    def __init__(self, namespace) -> None:
        self.watcher_num = 0
        self.namespace = namespace
        self.thread = None

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

            socketio.sleep(1)


class LocalPsutilMonitor(ResourceMonitor):
    def __init__(self, namespace) -> None:
        super().__init__(namespace)
        self.event = "response"
        self._hist_byte_sent = psutil.net_io_counters().bytes_sent
        self._hist_byte_recv = psutil.net_io_counters().bytes_recv
    
    def _get_net_speeds(self):
        net_byte_sent = psutil.net_io_counters().bytes_sent
        net_byte_recv = psutil.net_io_counters().bytes_recv
        net_input_speed = net_byte_recv - self._hist_byte_recv
        net_output_speed = net_byte_sent - self._hist_byte_sent
        self._hist_byte_sent = net_byte_sent
        self._hist_byte_recv = net_byte_recv
        return net_input_speed, net_output_speed
    
    def _get_cpu_index(self):
        exitcode, output = subprocess.getstatusoutput(
            "export LANG=en_US.UTF-8 && lscpu | grep -i '^model name:' | awk -F ': *' '{print $NF}'"
        )
        if exitcode == 0:
            return output
        return "unknown index"
    
    def _get_running_vm_num(self):
        exitcode, output = subprocess.getstatusoutput(
            "export LANG=en_US.UTF-8 && virsh list | grep running | wc -l"
        )
        if exitcode == 0:
            try:
                _ = int(output)
                return output
            except:
                return "unknown"

        return "unknown"
    
    def _get_disks_info(self):
        disks_total = 0
        disks_used = 0
        for disk in psutil.disk_partitions():
            if disk.mountpoint:
                disks_total += psutil.disk_usage(disk.mountpoint).total
                disks_used += psutil.disk_usage(disk.mountpoint).used
        
        disks_usage = disks_used / disks_total * 100

        return disks_total, disks_usage
    
    def get_data(self):
        system_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        cpu_usage = psutil.cpu_percent()
        cpu_physical_cores = psutil.cpu_count(logical=False)
        cpu_logical_cores = psutil.cpu_count()
        virtual_memory_usage = psutil.virtual_memory().percent
        virtual_memory_total = psutil.virtual_memory().total
        swap_memory_usage = psutil.swap_memory().percent
        swap_memory_total = psutil.swap_memory().total
        disks_total, disks_usage = self._get_disks_info()

        running_vm_num = self._get_running_vm_num()

        net_input_speed, net_output_speed = self._get_net_speeds()
        cpu_index = self._get_cpu_index()

        return {
            'system_time': system_time,
            'cpu_usage': cpu_usage,
            'cpu_physical_cores': cpu_physical_cores,
            'cpu_logical_cores': cpu_logical_cores,
            'virtual_memory_total': virtual_memory_total,
            'virtual_memory_usage': virtual_memory_usage,
            'swap_memory_total': swap_memory_total,
            'swap_memory_usage': swap_memory_usage,
            'disk_total': disks_total,
            'disk_usage': '%.1f' % disks_usage,
            'net_input_speed': net_input_speed,
            'net_output_speed': net_output_speed,
            'cpu_index': cpu_index,
            'running_vm_num': running_vm_num,
        }


class RemoteShellMonitor(ResourceMonitor):
    def __init__(self, namespace, ip) -> None:
        super().__init__(namespace)
        self.ip = ip
        self.event = ip
        self.ssh_client = None

    def _connect(self):
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self.ssh_client.connect(
                hostname=self.ip,
                username="root",
                port=22,
                password="openEuler12#$",
            )
        except (NoValidConnectionsError, SSHException) as e:
            self.ssh_client = None
    
    def disconnect(self):
        self.ssh_client.close()

    def _command(self, cli):
        stdin, stdout, stderr = self.ssh_client.exec_command(cli)
        return stdout.read().decode("utf-8")

    def get_data(self):
        self._connect()
        if not self.ssh_client:
            return {}

        mem_usage = self._command(CommonCli.mem_cli)
        cpu_usage= self._command(CommonCli.cpu_cli)
        os_info = self._command(CommonCli.os_cli)
        kernel_info = self._command(CommonCli.kernel_cli)

        self.ssh_client.close()

        return {
            "cpu_usage": float(cpu_usage.strip()),
            "mem_usage": float(mem_usage.strip()),
            "os_info": os_info.strip(),
            "kernel_info": kernel_info.strip(),
        }
