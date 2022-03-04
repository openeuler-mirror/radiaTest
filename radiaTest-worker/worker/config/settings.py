class Config(object):
    LOG_LEVEL = "INFO"
    LOG_PATH = "/var/log/mugen_work.log"
    STORAGE_POOL = "/var/lib/libvirt/images"
    NETWORK_INTERFACE_SOURCE = "br0"

    # Config.ini 文件目录
    CONFIG_INI_FILE_PATH = "/etc/radiaTest/worker.ini"
