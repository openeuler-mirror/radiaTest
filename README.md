# radiaTest

#### 介绍
版本级测试管理平台 Test Management Platform

- 版本级质量看板，使能社区版本测试可跟踪可追溯
- 文本用例统一看管，为社区文本用例的开发与评审提供基座
- 任务管理管理能力，实现测试活动全流程承载

#### 安装教程
一、 基于裸金属/虚拟机节点容器化部署
1.  安装web服务前后端（radiaTest-web & radiaTest-server）
    1) 待部署宿主机安装docker以及docker-compose软件包
    2) 执行 build/docker-compose/radiatestctl -u web 开启服务
    3) 按照交互引导部署服务，过程中填写证书相关信息(web服务端和messenger端的nginx服务均需求ssl证书)
    4）修改 /etc/radiaTest/server.ini配置文件
    5) 执行 build/docker-compose/radiatestctl -d web 关闭服务

二、基于k8s，部署节点为k8s-pod（目前仅覆盖radiaTest-web & radiaTest-server）
1. 通过 build/k8s-pod/web/nginx & build/k8s-pod/web/gunicorn
2. 准备 redis、rabbitmq、数据库，此部署模式需要人为准备中间件及数据库服务
3. 通过 挂载目录卷，将nginx、flask-app、gunicorn等所需的完整配置文件应用于相应容器
4. 运行 相应容器，检查日志和运行状态

    P.S.
    - 因采用配置文件初始化flask应用，中间件及数据库密码中不允许直接出现 # % 等歧义字符，若需使用必须使用转义
    - 配置文件中，不建议ip字段采用集群的域主机名，建议直接使用0.0.0.0，由外部保证访问安全
    - 日志均处于容器工作目录下的log中，可采取挂载目录卷的形式或同步存储于OBS桶的形式进行管理

#### 基于裸金属/虚拟机节点容器化部署的运维说明
若需要更改服务端口，或者docker的端口映射，请自行修改dockerfile或者docker-compose.yml
./gunicorn/gunicorn.conf.py决定了flask实际在docker中监听的端口
supervisor控制的进程日志均在./log中

1.  使用web服务前后端（radiaTest-web & radiaTest-server）
    1) docker exec -ti web_supervisor_1 bash
    2) 修改 /etc/radiaTest/server.ini 配置文件
    3) 执行supervisorctl交互式管理服务
    4) nginx配置文件位于宿主机/etc/nginx/nginx.conf，默认http监听8080，https监听443

#### 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支(可选)
3.  提交代码
4.  新建 Pull Request

#### Commit规范 && 质量要求

1.  commit格式
    1) commit名必须尊从格式 type(scope): subject
    2) type只允许使用以下标识:
        - feat：新功能（feature）
        - fix/to：修复bug，可以是QA发现的BUG，也可以是研发自己发现的BUG。
        - fix：产生diff并自动修复此问题。适合于一次提交直接修复问题
        - to：只产生diff不自动修复此问题。适合于多次提交。最终修复问题提交时使用fix
        - docs：文档（documentation）。
        - style：格式（不影响代码运行的变动）。
        - refactor：重构（即不是新增功能，也不是修改bug的代码变动）。
        - perf：优化相关，比如提升性能、体验。
        - test：增加测试。
        - chore：构建过程或辅助工具的变动。
        - revert：回滚到上一个版本。
        - merge：代码合并。
        - sync：同步主线或分支的Bug。
    3) scope为可选项，用于说明commit影响的范围（接口、类、方法）
    4) subject为commit描述，需少于50字符

2.  门禁要求
    1) 当且仅当门禁测试项均通过的PR才会予以合入
    2) 若门禁检查存在误判、非必要检查等问题，需要commit提交者登录MaJun平台将相应检查项提交屏蔽申请，并指定Ethan-Zhang进行评审
    3) 若屏蔽请求被通过，则PR将会在重跑结果合格后予以合入
    4) 若屏蔽请求被否决，则PR将会保持原状态，需要开发者完成相应修改后，手动/retest完成再次检查，门禁通过后@Ethan-Zhang通知合入

3.  测试覆盖
    1) 对于每一个PR，测试覆盖率均需达到80%测试覆盖的标准
    2) 对不涉及新特性、接口、类、方法的commit，PR评论中需要附上涉及的既有的测试结果/报告截图
    3) 对于涉及新特性、接口、类、方法的commit，PR中需要附加上相应的开发者自测用例，评论中需要涉及接口的测试结果/报告截图
    
4.  issue关联
    1) 对于fix/to类型的commit，需要关联响应issue，若仓库中缺乏描述被修复问题的issue，需要先创建issue后提交关联该issue的PR，否则不予合入

#### 联系方式

Ethan-Zhang:
    - EMAIL ethanzhang55@outlook.com

#### 特技

1.  使用 Readme\_XXX.md 来支持不同的语言，例如 Readme\_en.md, Readme\_zh.md
2.  Gitee 官方博客 [blog.gitee.com](https://blog.gitee.com)
3.  你可以 [https://gitee.com/explore](https://gitee.com/explore) 这个地址来了解 Gitee 上的优秀开源项目
4.  [GVP](https://gitee.com/gvp) 全称是 Gitee 最有价值开源项目，是综合评定出的优秀开源项目
5.  Gitee 官方提供的使用手册 [https://gitee.com/help](https://gitee.com/help)
6.  Gitee 封面人物是一档用来展示 Gitee 会员风采的栏目 [https://gitee.com/gitee-stars/](https://gitee.com/gitee-stars/)
