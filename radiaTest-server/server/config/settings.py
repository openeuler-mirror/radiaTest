# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    : 2022/09/20
# @License : Mulan PSL v2
#####################################

class Config(object):
    # Config.ini 文件目录
    INI_PATH = "/etc/radiaTest/server.ini"

    # 模式
    DEBUG = False
    TESTING = False

    # 日志
    LOG_LEVEL = "WARNING"
    LOG_CONF = "server/config/logging.json"

    # 数据库
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # API 官方版本
    OFFICIAL_API_VERSION = "v1"

    # 支持的架构
    SUPPORTED_ARCHES = ["aarch64", "x86_64"]

    # HTTP请求头
    HEADERS = {"Content-Type": "application/json;charset=utf8"}

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
    TMP_FILE_SAVE_PATH = "/opt/radiaTest/tmp/"

    # openEuler-QA团队配置
    # openEuler-QA团队名
    OE_QA_GROUP_NAME = "Kunpeng"

    # openEuler-QA update版本测试默认时长(days)
    OE_QA_UPDATE_TASK_PERIOD = 5

    # openEuler-QA文本用例格式规范
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
        "预期结果": "expection",
        "是否自动": "automatic",
        "是否自动化": "automatic",
        "备注": "remark",
    }

    # 每组测试环境，最大执行时长
    MAX_RUN_TIME = 3600

    # CASBIN
    CASBIN_MODEL = "/etc/radiaTest/casbinmodel.conf"
    CASBIN_OWNER_HEADERS = {"X-User", "X-Group", "Authorization"}
    CASBIN_USER_NAME_HEADERS = {"X-User", "X-Group", "Authorization"}

    # 创建虚拟机回调超时(单位:s)
    CALLBACK_EXPIRE_TIME = 3600

    # 需求涉及软件包的任务目标
    REQUIREMENT_PACKAGE_TARGETS = ["测试设计", "用例开发", "已执行", "问题分析"]

    OPENQA_SERVER = "openQA-server"

    STORE_AT_MAX_TIME = 172800

    # swagger
    SWAGGER_SWITCH = "off"  # 生产环境必须关闭
    SWAGGER_URL = "/static/api_docs"  # nginx代理原因, 必须以/static路径开头才能访问
    SWAGGER_YAML_FILE = "swagger.yaml"  # 实际api文件, 将文件放入

    # sqlalchemy
    SQLALCHEMY_POOL_SIZE = 20
    SQLALCHEMY_POOL_TIMEOUT = 300
    SQLALCHEMY_MAX_OVERFLOW = 10
    SQLALCHEMY_POOL_RECYCLE = 5400

    # 三方平台的信息
    YAML_PATH = "/etc/radiaTest/app.yaml"

    # 隐私声明版本
    PRIVACY_VERSION = "v1.0"

    # repo公网域名
    REPO_DOMAIN = "repo.openeuler.org"

    # gitee企业仓接口
    GITEE_ENTERPRISE = "https://api.gitee.com/enterprises"

    # openeuler release
    OPENEULER_RELEASE = "https://gitee.com/openeuler/release-management"

    # gitee v5 接口
    GITEE_V5 = "https://gitee.com/api/v5"


class TestingConfig(Config):
    TESTING = True
