class Config(object):
    LOG_LEVEL = "INFO"
    LOG_PATH = "/var/log/mugen_work.log"
    STORAGE_POOL = "/var/lib/libvirt/images"
    NETWORK_INTERFACE_SOURCE = "br0"

class DevelopmentConfig(Config):
    SERVER_IP = "172.168.131.14"
    SERVER_PORT = 1401

    WORKER_IP = "172.168.131.14"
    WORKER_PORT = 5000

class ProductionConfig(Config):
    SERVER_IP = "172.168.131.215"
    SERVER_PORT = 21510

    WORKER_IP = "172.168.131.215"
    WORKER_PORT = 5000