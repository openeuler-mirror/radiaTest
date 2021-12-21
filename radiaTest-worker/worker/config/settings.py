class Config(object):
    LOG_LEVEL = "INFO"
    LOG_PATH = "/var/log/radiaTest_worker.log"
    STORAGE_POOL = "/var/lib/libvirt/images"
    NETWORK_INTERFACE_SOURCE = "br0"

class DevelopmentConfig(Config):
    # SERVER_IP = xxxx
    # SERVER_PORT = xxxx

    # WORKER_IP = xxxx
    # WORKER_PORT = xxxx
    pass

class ProductionConfig(Config):
    # SERVER_IP = xxxx
    # SERVER_PORT = xxxx

    # WORKER_IP = xxxx
    # WORKER_PORT = xxxx
    pass