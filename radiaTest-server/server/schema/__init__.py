# @Author : lemon.higgins
# @Date   : 2021-10-15 17:03:38
# @Email  : lemon.higgins@aliyun.com
# @License: Mulan PSL v2


from typing_extensions import Literal

# 里程碑
##类型
MilestoneType = Literal["release", "round", "update"]

# 设备
## 架构
Frame = Literal["aarch64", "x86_64"]

## 物理机
### 释放占有
PmachineState = Literal["idle", "occupied"]

### 电源状态
Power = Literal["on", "off", "reset"]

## 虚拟机
### 安装方式
InstallMethod = Literal["auto", "import", "cdrom"]
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


# 测试用例
## 机器类型
MachineType = Literal["kvm", "physical"]

## 测试级别
TestLevel = Literal["系统测试", "集成测试", "单元测试"]

## 测试类型
TestType = Literal["功能测试", "安全测试", "性能测试", "压力测试", "可靠性测试"]

## 基线库节点类型
BaselineType = Literal["directory", "suite", "case"]


# 权限管理相关类型
## 角色类型
RoleType = Literal["public", "group", "organization"]
## RESTFUL请求类型
ActionType = Literal["post", "get", "delete", "put"]
## 效果类型
EffectType = Literal["allow", "deny"]

