<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0003：认证、权限和凭据(Authentication, Authorization, Credentials)

## 状态

已接受(Accepted)。

## 背景

radiaTest 需要简单明确的身份模型，固定三类角色：`ADMIN`、`TSE`、`TE`。Web 用户需要浏览器登录；脚本和外部集成需要 API 访问能力，但不能复用浏览器凭据。即使在内网环境，SSH/BMC 凭据也需要基本保护和审计。

## 决策

采用：

- 只支持本地账号(Local Account)。
- 不支持 Web 自助注册。
- Web 会话使用 JWT 访问令牌(Access Token)。
- Web JWT 访问令牌有效期为 1 天。
- 脚本/API 使用个人访问令牌(Personal Access Token, PAT)。
- PAT 明文只在创建时展示一次，数据库只保存哈希(Hash)。
- PAT 权限继承所属用户当前有效角色。
- 资源凭据使用 Fernet 做应用层加密(Application-Layer Encryption)。
- 凭据查看通过独立 API 并执行后端鉴权。
- 不记录凭据查看行为，凭据修改写审计日志。

不实现 GitHub、AtomGit 等 OAuth Provider 作为 Web 登录方式。可以增加 `user_identities`
绑定外部身份，但角色仍由 radiaTest 管理员配置；飞书身份绑定只用于飞书 Bot 识别操作者。

## 角色规则

`ADMIN`：

- 管理用户和角色。
- 管理全部资源和资源池。
- 导入资源和租约，导出资源。
- 占用关键资源。
- 查看全部凭据。
- 续期自己的有限期租约。
- 强制释放任何租约。
- 查看全部审计日志和租约日志。

`TSE`：

- 管理资源池。
- 创建和编辑 active 资源，但不能编辑被别人占用的资源。
- 占用非关键的 active idle 资源。
- 只有占用期间才能查看非关键资源凭据。
- 释放和续期自己的租约。
- 只能强制释放 `TE` 租约。
- 查看全部租约日志。
- 不能访问审计日志页面。

`TE`：

- 查看资源公共信息。
- 占用非关键的 active idle 资源。
- 释放和续期自己的租约。
- 只有占用期间才能查看非关键资源凭据。
- 不能编辑资源。
- 不能强制释放他人租约。
- 不能访问审计日志页面。

## 凭据规则

- 物理资源必须有主 IP 和 SSH 凭据；自动安装方式创建的虚拟资源必须有 SSH 凭据。
- VM 创建出的虚拟资源默认保存 SSH 账号 `root` 和密码 `openEuler12#$`，自动和手动安装方式一致。
- 物理资源额外必须有 BMC 凭据。
- 虚拟资源没有 BMC 凭据。
- 凭据以加密字段保存在资源表或规格表内。
- 前端不能持久化展示后的明文凭据。
- 凭据查看不写审计日志。
- 凭据新增、修改和清除写审计日志。
- 关键资源只能由 `ADMIN` 占用。
- 关键资源凭据只能由 `ADMIN` 查看。

## 幂等性(Idempotency)

关键写接口使用 `Idempotency-Key`。后端在执行副作用前原子占用 key；同一用户、同一方法、
同一路径、同一个 key 且请求哈希一致时，返回第一次响应，仍在处理时返回稳定冲突错误；
同一个 key 携带不同参数时返回冲突。key 长度限制为 1～255 个字符。前端对相同请求的重试
复用原 key，请求参数变化后生成新 key。自动清理只删除已完成记录；外部副作用结果不确定的
处理中记录不自动删除，避免清理后重复执行。

必须支持：

- 占用。
- 释放。
- 续期。
- 强制释放。
- VM 申请。
- VM 释放。
- VM 电源操作。
- 测试任务创建。
- 导入确认。

## 影响

- Web 登录和脚本/API 访问分离。
- 禁用用户、修改角色或撤销 PAT 后，不需要暴露令牌明文即可生效。
- 凭据变更可以被审计。
- API 客户端可以安全重试关键资源状态变更。
