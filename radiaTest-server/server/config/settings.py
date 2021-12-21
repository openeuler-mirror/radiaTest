class Config(object):
    # nginx 没有nginx代理时，请使用后端服务的端口
    NGINX_LISTEN = '1401'

    # 模式
    DEBUG = False
    TESTING = False

    # 日志
    LOG_PATH = "/var/log/Mugen.log"
    LOG_LEVEL = "INFO"

    # 数据库
    SQLALCHEMY_DATABASE_URI = "mysql://root@127.0.0.1/mugen"
    SQLALCHEMY_POOL_SIZE = 100
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Redis
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    # REDIS_PASSWORD = "123"
    REDIS_DB = 11

    # Gitee oauth login
    GITEE_OAUTH_CLIENT_ID = "7b85571d5342bd00f53c392908e8438f80ff84358d4187a9dd062db1df8c8819"
    GITEE_OAUTH_CLIENT_SECRET = "152bd73521b127f01a1ae8468051ae8e72d5f418055c44a65c9171d270215952"
    GITEE_OAUTH_REDIRECT_URI = "http://123.60.114.22:1400/api/v1/gitee/oauth/callback"
    GITEE_OAUTH_HOME_URL = "http://123.60.114.22:1400/login"
    GITEE_OAUTH_SCOPE = ['user_info', 'emails', 'enterprises', 'issues']

    # Token
    TOKEN_SECRET_KEY = "lPrn3bC4Iz7JoQcNDjOFS2m6sapqH8wA"
    TOKEN_EXPIRES_TIME = 600

    # SERVER CONFIG
    SERVER_IP = "172.168.131.14"
    SERVER_PORT = 1401

    # WEBSOCKIFY 监听端口
    WEBSOCKIFY_LISTEN = 1480

    # 物理机
    ## CI宿主机标志
    CI_SIGN = "as the host of ci"
    ## CI测试机标志
    CI_PURPOSE = "used for ci"

    ## 物理机最长占用时间(days)
    MAX_OCUPY_TIME = 7

    ## 物理机默认占用时间(days)
    DEFAULT_OCUPY_TIME = 1

    # PXE服务器
    ## PXE地址(必须配置免密登录，如果和server为同一台机器，则不需要)
    PXE_IP = "172.168.131.94"
    PXE_SSH_USER = "root"
    PXE_SSH_PORT = 22
    PRIVATE_KEY = "/root/.ssh/id_rsa"

    ## dhcp配置文件
    DHCP_CONF = "/etc/dhcp/dhcpd.conf"

    ## tftp-server 文件存储路径
    TFTP_PATH = "/var/lib/tftpboot"

    # 存储服务器
    ## httpd信息
    REPO_IP = "172.168.131.94"
    REPO_PORT = 9400
    LOGS_ROOT_URL = "mugen.logs"
    ## rsyncd信息
    RSYNC_USER = "root"
    RSYNC_MODULE = "mugen"
    RSYNC_PASSWORD = "mugen@1234"
    RSYNC_PASSWORD_FILE = "/tmp/rsync.pass"

    # Worker节点
    ## 消息头
    HEADERS = {"Content-Type": "application/json;charset=utf8"}

    ## 通信协议
    PROTOCOL = "http"

    # 虚拟机
    ## 虚拟机创建基础信息
    ### 最大内存
    VM_MAX_MEMEORY = 16384

    ### 最大core量
    VM_MAX_CORE = 4

    ### 最大thread量
    VM_MAX_THREAD = 4

    ### 最大socket量
    VM_MAX_SOCKET = 4

    ### 最大磁盘大小(G)
    VM_MAX_CAPACITY = 500

    ## pxe安装，mac地址绑定网段
    RANDOM_IP_POOL = "172.168.131"

    ## 等待虚拟机建立通信时长
    VM_ENABLE_SSH = 300

    ## 默认存活时长(days)
    VM_DEFAULT_DAYS = 7

    ## 最大存活时长(days)
    VM_MAX_DAYS = 15

    # NTP server
    NTP_SERVER = [
        "1.cn.pool.ntp.org",
        "2.cn.pool.ntp.org",
        "3.cn.pool.ntp.org",
        "0.cn.pool.ntp.org",
        "cn.pool.ntp.org",
        "tw.pool.ntp.org",
        "0.tw.pool.ntp.org",
        "1.tw.pool.ntp.org",
        "2.tw.pool.ntp.org",
        "3.tw.pool.ntp.org",
    ]

    # 上传服务端文件的暂存地址
    UPLOAD_FILE_SAVE_PATH = "/tmp/"

    # openEuler-QA团队配置
    ## openEuler-QA团队名
    OE_QA_GROUP_NAME = "openeuler-QA"

    ## openEuler-QA update版本测试默认时长(days)
    OE_QA_UPDATE_TASK_PERIOD = 5

    ## openEuler-QA文本用例格式规范
    OE_QA_TESTCASE_DICT = {
        "测试套": "suite", 
        "用例名": "name", 
        "测试级别": "test_level", 
        "测试类型": "test_type", 
        "用例描述": "description", 
        "节点数": "machine_num", 
        "预置条件": "preset", 
        "操作步骤": "steps", 
        "预期输出": "expection",
        "是否自动": "automatic",
        "是否自动化": "automatic",
        "备注": "remark",
    }
    

    # 执行任务
    ## 服务端mugen框架存放路径
    SERVER_FRAMEWORK_PATH = "/tmp"

    ## 测试机上mugen框架存放路径
    TEST_MACHINE_FRAMEWORK_PATH = "/opt"

    ## 每组测试环境，最大执行时长
    MAX_RUN_TIME = 3600


class ProductionConfig(Config):
    # server
    SERVER_IP = '172.168.131.215'
    SERVER_PORT = 21510

    SQLALCHEMY_DATABASE_URI = "mysql://root:root@172.168.131.215/mugen"
    # Gitee oauth login
    GITEE_OAUTH_CLIENT_ID = "a7c1a9d429d5093af5c94a55f80719d741159377b905a1785c64756e1be7541c"
    GITEE_OAUTH_CLIENT_SECRET = "0310115de51eb21835468e0a00a50a9b9c998694b220d075e00ba8ff7f3c0ee9"
    GITEE_OAUTH_REDIRECT_URI = "http://123.60.114.22:21500/api/v1/gitee/oauth/callback"
    GITEE_OAUTH_HOME_URL = "http://123.60.114.22:21500/login"

    NGINX_LISTEN = '21500'

    # WEBSOCKIFY 监听端口
    WEBSOCKIFY_LISTEN = 21580


class DevelopmentConfig(Config):
    DEBUG = True
    # Gitee oauth login
    GITEE_OAUTH_CLIENT_ID = "ca793f8540b6182f8beaf35c657e287de59a637ac36b40e852cab3f2bc2ed0fb"
    GITEE_OAUTH_CLIENT_SECRET = "21c205de7e7540ae73d577c4459e7bb261eeb433538a9820703ea3e628e46642"
    GITEE_OAUTH_REDIRECT_URI = "http://192.168.0.155:9200/api/v1/gitee/oauth/callback"
    GITEE_OAUTH_HOME_URL = "http://192.168.0.155:9200/login"

    SERVER_IP = '0.0.0.0'
    SERVER_PORT = 9201

    NGINX_LISTEN = '9201'


class TestingConfig(Config):
    TESTING = True