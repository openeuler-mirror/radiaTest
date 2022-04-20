# radiaTest

#### 介绍
版本级测试管理平台 Test Management Platform

- 版本级质量看板，使能社区版本测试可跟踪可追溯
- 多元化资源池，无障碍对接各类资源管理系统和组网
- 文本用例统一看管，为社区文本用例的开发与评审提供基座
- 多元化测试引擎，满足社区差异化测试能力需求，灵活选用
- 任务管理管理能力，实现测试活动全流程承载

#### 架构简介
radiaTest-web & radiaTest-server: web服务的前后端
- 若需要本地化部署测试管理平台web服务，则需部署（推荐使用radiatest.openeuler.org提供的公共服务）

radiaTest-messenger: 接入机器组的请求转发与处理服务
- 机器组的堡垒/跳板节点，与radiaTest-server单点通信
- 部署于内网/外网跳板机，或NAT映射后部署在内网的机器上
- 在web服务注册相应机器组后，个人/团队/组织管理者在对应机器上按需布置

radiaTest-worker: 动态资源(虚机资源)管理服务
- 部署于物理宿主机，用于接受动态资源相关请求，完成实际虚机资源管理
- 可部署于机器组内网，仅与messenger节点通信（推荐）
- 若部署于公网机器，则需保证属于公网机器组，且可于对应机器组的messenger节点通信


#### 安装教程
radiaTest-worker必须部署在服务器物理环境

一、 基于裸金属/虚拟机节点容器化部署
    1.  安装web服务前后端（radiaTest-web & radiaTest-server）
        - 1) 待部署宿主机安装docker以及docker-compose软件包
        - 2) 执行 build/direct/lib/up_web_server 脚本
    2.  安装messenger服务端（radiaTest-messenger）
        - 1) 待部署宿主机安装docker以及docker-compose软件包
        - 2) 执行 build/direct/lib/up_messenger_server 脚本
    3.  安装worker服务端（radiaTest-worker）
        - 1) 执行 build/direct/lib/up_worker_server 脚本

二、基于k8s，部署节点为k8s-pod（目前仅覆盖radiaTest-web & radiaTest-server）
    1. 通过 build/k8s-pod/web/nginx & build/k8s-pod/web/supervisor 构建docker镜像
    2. 准备 redis、rabbitmq、数据库，此部署模式需要人为准备中间件及数据库服务
    3. 通过 挂载目录卷，将nginx、flask-app、gunicorn等所需的完整配置文件应用于相应容器
    4. 运行 相应容器，检查日志和运行状态

    P.S.
        1）因采用配置文件初始化flask应用，中间件及数据库密码中不允许直接出现 # % 等歧义字符，若需使用必须使用转义
        2）配置文件中，不建议ip字段采用集群的域主机名，建议直接使用0.0.0.0，由外部保证访问安全
        3）日志均处于容器工作目录下的log中，可采取挂载目录卷的形式或同步存储于OBS桶的形式进行管理

#### 基于裸金属/虚拟机节点容器化部署的运维说明
若需要更改服务端口，或者docker的端口映射，请自行修改dockerfile或者docker-compose.yml
./gunicorn/gunicorn.conf.py决定了flask实际在docker中监听的端口
supervisor控制的进程日志均在./log中

1.  使用web服务前后端（radiaTest-web & radiaTest-server）
    - 1) docker exec -ti web_supervisor_1 bash
    - 2) 修改 /etc/radiaTest/server.ini 配置文件
    - 3) 执行supervisorctl交互式管理服务
    - 4) nginx配置文件位于宿主机/etc/nginx/nginx.conf，默认http监听8080，https监听443

2.  使用messenger服务端（radiaTest-messenger）
    - 1) docker exec -ti messenger_supervisor_1 bash
    - 2) 修改 /etc/radiaTest/messenger.ini 配置文件
    - 3) 执行supervisorctl交互式管理服务

3.  使用worker服务端（radiaTest-worker）
    - 1) 执行supervisorctl交互式管理服务

#### 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支(可选)
3.  提交代码
4.  新建 Pull Request

#### 联系方式

Ethan-Zhang:
    - TEL   13430919587
    - EMAIL ethanzhang55@outlook.com

#### 特技

1.  使用 Readme\_XXX.md 来支持不同的语言，例如 Readme\_en.md, Readme\_zh.md
2.  Gitee 官方博客 [blog.gitee.com](https://blog.gitee.com)
3.  你可以 [https://gitee.com/explore](https://gitee.com/explore) 这个地址来了解 Gitee 上的优秀开源项目
4.  [GVP](https://gitee.com/gvp) 全称是 Gitee 最有价值开源项目，是综合评定出的优秀开源项目
5.  Gitee 官方提供的使用手册 [https://gitee.com/help](https://gitee.com/help)
6.  Gitee 封面人物是一档用来展示 Gitee 会员风采的栏目 [https://gitee.com/gitee-stars/](https://gitee.com/gitee-stars/)
