class Config(object):
    # Config.ini 文件目录
    INI_PATH = "/etc/radiaTest/messenger.ini"

    # 模式
    DEBUG = False
    TESTING = False

    # 日志
    LOG_LEVEL = "INFO"

    # PXE服务器
    # PXE地址(必须配置免密登录，如果和server为同一台机器，则不需要)
    # dhcp配置文件
    DHCP_CONF = "/etc/dhcp/dhcpd.conf"

    # tftp-server 文件存储路径
    # TFTP_PATH = "/var/lib/tftpboot"

    # HTTP请求头
    HEADERS = {"Content-Type": "application/json;charset=utf8"}

    # HTTP PROTOCOL
    PROTOCOL = "http"

    # 虚拟机
    # 虚拟机创建基础信息
    # 最大内存
    VM_MAX_MEMEORY = 16384

    # 最大core量
    VM_MAX_CORE = 4

    # 最大thread量
    VM_MAX_THREAD = 4

    # 最大socket量
    VM_MAX_SOCKET = 4

    # 最大磁盘大小(G)
    VM_MAX_CAPACITY = 500

    # 等待虚拟机建立通信时长
    VM_ENABLE_SSH = 300

    # 默认存活时长(days)
    VM_DEFAULT_DAYS = 7

    # 最大存活时长(days)
    VM_MAX_DAYS = 15

    # 上传服务端文件的暂存地址
    UPLOAD_FILE_SAVE_PATH = "/tmp/"

    # 执行任务
    # worker端框架存放路径
    WORKER_DOWNLOAD_PATH = "/opt"

    # 每组测试环境，最大执行时长
    MAX_RUN_TIME = 3600


class TestingConfig(Config):
    TESTING = True
