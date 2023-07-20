# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

from typing_extensions import Literal

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

#权限归属
PermissionType = Literal["person", "group", "org", "public"]

