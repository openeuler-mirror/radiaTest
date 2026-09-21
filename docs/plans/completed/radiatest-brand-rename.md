<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# radiaTest 品牌替换(Kronos → radiaTest v2.0)

## 背景

Kronos 现定位为 radiaTest v2.0。用户已提供新 logo(workspace 根 `logo.svg`)。Grill 确认:

1. **替换范围 = 品牌层**:UI 文案/应用名/登录页 logo/文档品牌名/csv 下载名;**不动运行时标识**(数据库 kimariyb_kronos、路径 /opt/kimariyb-kronos 与 /opt/kronos、/etc/kronos、KRONOS_EVENT/KRONOS_PAYLOAD_B64 宿主协议、docker 镜像与容器名、compose 项目名、VITE_APP_NAMESPACE 'kronos'、包名 kronos-backend),避免破坏两套已部署环境与宿主机脚本协议。
2. **命名**:显示名统一 `radiaTest`(camelCase);定位以"radiaTest v2.0(原 Kronos)"表述出现在 README 等说明性位置,不作为常驻 UI 标题。

## 范围

- Logo:复制 `logo.svg` 到 `frontend/apps/web-antd/public/`,覆盖 Vben 默认远程 logo(`preferences.ts` 增 `logo.source: '/logo.svg'`)。
- UI:`VITE_APP_TITLE` 'Kronos'→'radiaTest'(vite.config.ts)、dashboard 页名、账号页飞书文案 2 处、资源导出 csv 名 `kronos-resources.csv`→`radiaTest-resources.csv`。
- 文档:README、AGENTS.md、CONTRIBUTING.md、CONTEXT.md、docs/(adr/spec/plans/runbook)品牌词替换;README 开头写定位"radiaTest v2.0(原 Kronos)"。
- 后端:注释/docstring/用户可见消息中的品牌词替换(31 文件,逐个确认,不做盲目 sed);包名 `kronos-backend` 不动。
- 替换规则:仅替换独立品牌词 "Kronos";带连字符/下划线的标识符(kimariyb-kronos、kronos_dev、kronos-resources 下载名除外、镜像名)一律保留。

## 明确不做

- 不改运行时标识与部署路径,不做服务器侧迁移。
- 不改 git 仓库名/远端(atomgit/gitcode 平台侧操作)。
- 不改 favicon.ico(用户提供的是 SVG;如需 ico 另行处理)。
- 不改 .serena/project.yml 等本地工具配置。

## 实施步骤

1. Logo 接入 + preferences 配置。
2. UI 品牌词与 csv 下载名。
3. 文档品牌词替换(含定位说明),逐文件 review,不误伤运行时标识。
4. 后端注释/消息品牌词替换。
5. 定向测试(preferences.test.ts 等)+ `./scripts/check.sh`。

## 验证标准

- `grep -rn "Kronos"` 仅剩:定位说明"(原 Kronos)"一处、运行时标识语境(kimariyb-kronos 等非品牌词)、明确保留项。
- 前端定向测试与 check.sh 通过。
