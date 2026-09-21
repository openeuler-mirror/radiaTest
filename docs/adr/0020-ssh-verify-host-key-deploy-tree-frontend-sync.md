<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0020：mugen_runner SSH 跳过 host key 验证 + 节点跳转按 env_type + 部署树前端同步

日期: 2026-07-28

## 状态

已采纳。

## 背景

物理机 PXE 重装后 host key 变化,mugen_runner 的 SSH 连接报 `REMOTE HOST IDENTIFICATION HAS CHANGED`。根因:`run_control_command` 走 `run_remote_bash_command`,后者写死 `StrictHostKeyChecking=accept-new`(不覆盖冲突 key)。之前只修了 `run_ssh_command`(加 `verify_host_key=False`),但 mugen_runner 走的是另一条 SSH 路径。

节点 IP 点击跳转:`openNode` 改成按 `node.env_type` 跳转(已实现),但前端镜像构建时从 `/opt/kronos/dev/app/`(部署树)取源,工作区的改动没同步到部署树 → 重建出来的前端还是旧的。

## 决策

### 1. run_remote_bash_command 加 verify_host_key 参数

`run_remote_bash_command` 加 `verify_host_key: bool = True` 参数(跟 `run_ssh_command` 一致)。`verify_host_key=False` 时用 `StrictHostKeyChecking=no` + `UserKnownHostsFile=/dev/null`。

`run_control_command` 默认 `verify_host_key=False`(测试框架连的机器都可能被重装,host key 不该阻塞执行)。

不采用:全局改 `run_remote_bash_command` 默认 False——它可能被非测试框架代码用(VM 创建等),那些场景 host key 检查有意义。只改 `run_control_command` 的默认。

### 2. 部署树前端同步

重建前端镜像前,必须把工作区的 `run-job-detail.vue` 等前端改动同步到 `/opt/kronos/dev/app/frontend/`。否则构建出来的镜像缺最新前端代码。

不采用:从工作区构建前端镜像——构建上下文(Dockerfile 路径)指向部署树,改上下文路径有风险。

### 3. 节点跳转按 node.env_type(已实现,需重建)

`openNode(resource_id, node.env_type)` —— 按**节点自己的** env_type 跳转,不看 RunJob 的 env_type(both 时为 null)。已实现,但因部署树不同步未生效。

## 影响

- `remote.py`:`run_remote_bash_command` 加 `verify_host_key` 参数。
- `mugen_runner.py`:`run_control_command` 传 `verify_host_key=False`。
- 部署流程:重建前端前先 `rsync` 工作区前端到部署树。
- spec 0003 + CONTEXT 同步。
