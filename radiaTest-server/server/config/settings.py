# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : Ethan-Zhang,凹凸曼打小怪兽
# @email   : 15710801006@163.com
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

    # Gitee oauth login 通用配置
    GITEE_OAUTH_SCOPE = ['user_info', 'emails', 'enterprises', 'issues']

    # API 官方版本
    OFFICIAL_API_VERSION = "v1"

    # 支持的架构
    SUPPORTED_ARCHES = ["aarch64", "x86_64"]

    # 物理机
    # CI宿主机标志
    CI_HOST = "as the host of ci"
    # CI测试机标志
    CI_PURPOSE = "used for ci"

    # 物理机最长占用时间(days)
    MAX_OCUPY_TIME = 7

    # 物理机默认占用时间(days)
    DEFAULT_OCUPY_TIME = 1

    # tftp-server 文件存储路径
    # TFTP_PATH = "/var/lib/tftpboot"

    # HTTP请求头
    HEADERS = {"Content-Type": "application/json;charset=utf8"}

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

    # 最大创建虚拟机数量
    VM_MAX_COUNT = 10

    # 最大磁盘大小(G)
    VM_MAX_CAPACITY = 500

    # 等待虚拟机建立通信时长
    VM_ENABLE_SSH = 300

    # 默认存活时长(days)
    VM_DEFAULT_DAYS = 7

    # 最大存活时长(days)
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
    TMP_FILE_SAVE_PATH = "/tmp/"

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

    # 执行任务
    # 服务端框架存放路径
    SERVER_DOWNLOAD_PATH = "/tmp"

    # 每组测试环境，最大执行时长
    MAX_RUN_TIME = 3600

    # CASBIN
    CASBIN_MODEL = "/etc/radiaTest/casbinmodel.conf"
    CASBIN_OWNER_HEADERS = {"X-User", "X-Group", "Authorization"}
    CASBIN_USER_NAME_HEADERS = {"X-User", "X-Group", "Authorization"}

    # 创建虚拟机回调超时(单位:s)
    CALLBACK_EXPIRE_TIME = 3600

    # 默认虚拟机容量(单位:G)
    VM_DEFAULT_CAPACITY = 50

    # 需求涉及软件包的任务目标
    REQUIREMENT_PACKAGE_TARGETS = ["测试设计", "用例开发", "已执行", "问题分析"]

    OPENQA_SERVER = "openQA-server"

    STORE_AT_MAX_TIME = 172800


class TestingConfig(Config):
    TESTING = True
