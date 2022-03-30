from typing_extensions import Literal

# 设备
## 架构
Frame = Literal["aarch64", "x86_64"]

### 电源状态
Power = Literal["on", "off", "reset"]

## 虚拟机
### 安装方式
InstallMethod = Literal["auto", "import", "cdrom"]

### 物理机选择方式
PmSelectMode = Literal["auto", "assign"]

### 状态
VMStatus = Literal[
    "start", "destroy", "shutdown", "reset", "reboot", "suspend", "resume"
]

### cpu模式
CPUMode = Literal["host-passthrough", "host-model", "custom"]

### 网络
#### 总线
NetBus = Literal["virtio", "e1000e", "e1000", "rtl8139"]

#### 模式
NetMode = Literal["bridge", "network"]

### 磁盘
#### 总线
DiskBus = Literal["virtio", "sata", "scsi", "usb"]

#### 缓存
DiskCache = Literal[
    "default", "none", "writethrough", "writeback", "directsync", "unsafe"
]

### 播放总线
VideoBus = Literal["virtio"]

# 机器
## 机器类型
MachineType = Literal["kvm", "physical"]
## 机器用途
MachinePurpose = Literal["create_vmachine", "run_job"]
# 测试执行
## Job执行机器选取策略
MachinePolicy = Literal["auto", "manual"]

