import time
import psutil
import subprocess

class ResourceMonitor:
    def __init__(self) -> None:
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