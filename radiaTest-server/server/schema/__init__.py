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


#操作符
Operator = Literal["<", ">", "=", "<=", ">="]

# 排序
SortOrder = Literal["ascend", "descend"]

# 里程碑
##类型
MilestoneType = Literal["release", "round", "update"]
## 状态
MilestoneState = Literal["active", "closed"]
## 状态事件
MilestoneStateEvent = Literal["activate", "close"]

# 设备
## 架构
Frame = Literal["aarch64", "x86_64"]

# 资源池
## 机器组
MachineGroupNetworkType = Literal["WAN", "LAN"]

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

## 机器类型
MachineType = Literal["kvm", "physical"]
## 机器用途
MachinePurpose = Literal["create_vmachine", "run_job"]


# 测试用例
## 测试级别
TestLevel = Literal["系统测试", "集成测试", "单元测试"]

## 测试类型
TestType = Literal["功能测试", "安全测试", "性能测试", "压力测试", "可靠性测试"]

## 基线库节点类型
CaseNodeType = Literal["directory", "suite", "case", "baseline"]

#权限归属
PermissionType = Literal["person", "group", "org", "public"]

## 测试策略导入文件类型
StrategyImportFileType = Literal["md", "yaml", "json", "New"]

# 测试策略提交状态
StrategyCommitStatus = Literal["staged", "submitted"]

#提交类型
CommitType = Literal['week', 'halfMonth', 'month']

# 测试执行
## Job排序依据
JobSortedBy = Literal["create_time", "end_time"]
## Job分表依据
JobDefaultStates = Literal["PENDING", "DONE"]
## Job执行机器选取策略
MachinePolicy = Literal["auto", "manual"]



# 权限管理相关类型
## 角色类型
RoleType = Literal["person", "group", "org", "public"]
## RESTFUL请求类型
ActionType = Literal["post", "get", "delete", "put"]
## 效果类型
EffectType = Literal["allow", "deny"]


# 需求附件类型
AttachmentType = Literal["statement", "progress", "validation"]

# 需求发布/接受类型
RequirementAcceptType = Literal["person", "group"]
RequirementPublishType = Literal["person", "group", "organization"]

# 日志类型
LoggingType = Literal["info", "warning", "success", "error"]

# 基线模板类型
BaselineTemplateType = Literal["group", "org"]

#鉴权机构
Authority = Literal["gitee", "oneid", "default"]
