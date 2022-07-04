import os
import configparser
from pathlib import Path


class RET(object):
    OK = "2000"
    OTHER_REQ_ERR = "3500"
    OTHER_REQ_TIMEOUT = "3504"
    PARMA_ERR = "4000"
    VERIFY_ERR = "4001"
    CLA_VERIFY_ERR = "4010"
    UNAUTHORIZE_ERR = "4020"
    BAD_REQ_ERR = "4050"
    SERVER_ERR = "5000"
    DATA_EXIST_ERR = "5001"
    DB_ERR = "5002"
    NO_DATA_ERR = "5003"
    DB_DATA_ERR = "5004"
    FILE_ERR = '6000'
    DATA_DEL_ERR = "30006"
    SYS_CONF_ERR = "30007"
    WRONG_INSTALL_WAY = "30010"
    INSTALL_CONF_ERR = "50008"
    NET_CONF_ERR = "50009"
    NET_CONECT_ERR = "50010"
    NO_MEM_ERR = "50011"
    TASK_WRONG_GROUP_NAME = "60001"
    WRONG_REPO_URL = "60002"
    RUNTIME_ERROR = "60009"
    CASCADE_OP_ERR = "60010"
    CERTIFICATE_VERIFY_FAILED = "5009"
    SSLERROR = "5010"


def loads_ini(ini_path, section, option):
    config_ini = Path(ini_path)

    cfg = configparser.ConfigParser()
    cfg.read(config_ini)

    try:
        return cfg.get(section, option)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return ''

_path = os.path.abspath(os.path.dirname(__file__))

account = loads_ini(f"{_path}/../api-test.ini", "server", "admin_account")
password = loads_ini(f"{_path}/../api-test.ini", "server", "admin_password")
server_url = loads_ini(f"{_path}/../api-test.ini", "server", "server_url")
repo_url = loads_ini(f"{_path}/../api-test.ini", "rsync", "repo_url")
gitee_id = loads_ini(f"{_path}/../api-test.ini", "server", "gitee_id")

default_headers = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "Connection": "keep-alive",
    "Accept-Encoding": "gzip, deflate, br",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36",
}