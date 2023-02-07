class Config(object):
    LOG_LEVEL = "INFO"

    # HTTP 请求头
    HEADERS = {"Content-Type": "application/json;charset=utf8"}

    # Config.ini 文件目录
    CONFIG_INI_FILE_PATH = "/etc/radiaTest/worker.ini"

    VNC_START_PORT = 5900
