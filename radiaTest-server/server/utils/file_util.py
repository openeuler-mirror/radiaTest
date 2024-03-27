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
# @Date    :
# @License : Mulan PSL v2
#####################################

import os
import re
import datetime
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid1
from shlex import quote
from werkzeug.utils import secure_filename
import pytz

import magic
from flask import current_app, jsonify
from pypinyin import lazy_pinyin

from server.utils.response_util import RET
from server import redis_client
from server.utils.shell import run_cmd


class FileUtil(object):

    @staticmethod
    def flask_save_file(file_storage, file_path):
        if not file_storage or not file_path:
            return None
        try:
            file_path_temp = file_path.split(current_app.static_url_path, 1)[1]
            file_suffix = os.path.splitext(secure_filename(file_storage.filename))[-1]
            file_storage.save(f'{current_app.static_folder}{file_path_temp}{file_suffix}')

            return f'https://{current_app.config.get("SERVER_ADDR")}' \
                   f'{current_app.static_url_path}{file_path_temp}{file_suffix}'.replace(os.path.sep, '/')

        except Exception as e:
            current_app.logger.error(f'file save error{e}')
        return None

    @staticmethod
    def generate_filepath(static_dir):
        file_save_dir = f'{current_app.static_folder}{os.path.sep}{static_dir}'
        if not os.path.exists(file_save_dir):
            os.makedirs(file_save_dir)
        return f'{current_app.static_url_path}{os.path.sep}{static_dir}{os.path.sep}{uuid1().hex}'


class ImportFile:
    def __init__(self, file, filename=None, filetype=None) -> None:
        self.file = file
        self.filepath = None
        self.valid_types = [".+"]
        self.filename = filename
        self.filetype = filetype
        if not filename and not filetype:
            self.filename, self.filetype = self._validate_filetype()

    def file_save(self, tmp_path, timestamp=True):
        if timestamp:
            self.filepath = os.path.join(
                tmp_path,
                secure_filename(
                    ''.join(
                        lazy_pinyin(
                            "{}.{}.{}".format(
                                self.filename,
                                datetime.datetime.now(tz=pytz.timezone('Asia/Shanghai')).strftime("%Y%m%d%H%M%S"),
                                self.filetype
                            )
                        )
                    )
                )
            )
        else:
            self.filepath = os.path.join(
                tmp_path,
                secure_filename(
                    ''.join(
                        lazy_pinyin(
                            "{}.{}".format(
                                self.filename,
                                self.filetype
                            )
                        )
                    )
                )
            )

        if os.path.exists(self.filepath):
            raise RuntimeError("Filepath is already exist: {}".format(self.filepath))

        self.file.save(self.filepath)

    def file_remove(self):
        if self.filepath is None:
            raise RuntimeError("This file could not be removed, due to not exist")

        cmd = "rm -rf {}".format(quote(self.filepath))
        _, _, _ = run_cmd(cmd)

    def _validate_filetype(self):
        pattern = r'^([^\.].*?)\.({})$'.format('|'.join(self.valid_types))
        result = re.search(pattern, self.file.filename)
        if not result:
            return "", ""
        return result[1], result[2]


class ZipImportFile(ImportFile):
    def __init__(self, file) -> None:
        super().__init__(file)
        self.valid_types = [
            "rar",
            "zip",
            "tar",
            "tar.gz",
            "tar.xz",
            "tar.bz2"
        ]
        self.macos_cache = "__MACOSX"
        self.filename, self.filetype = self._validate_filetype()

    def uncompress(self, uncompressed_filepath):
        # 赋予uncompress解压目录权限
        _, _, _ = run_cmd("mkdir -p '{}' && chmod 777 '{}'".format(uncompressed_filepath, uncompressed_filepath))
        # 赋予解压文件可读权限
        _, _, _ = run_cmd("chmod 755 '{}'".format(self.filepath))
        # 使用uncompress普通用户,安全解压
        safe_uncompress = Path(__file__).parent.joinpath("safe_uncompress.py")
        _, data, error = run_cmd("sudo -u uncompress python3 '{}' -t '{}' -f '{}' -d '{}'".format(
            safe_uncompress, self.filetype, self.filepath, uncompressed_filepath))
        if "uncompress success!" in data:
            _, _, _ = run_cmd("sudo -u uncompress chmod -R 755 '{}'".format(uncompressed_filepath))
            return True
        else:
            current_app.logger.error(f"data: {data}, error: {error}")
            self.clean_and_delete(uncompressed_filepath)
            return False

    def clean_and_delete(self, uncompressed_filepath=None):
        if os.path.exists(self.filepath):
            self.file_remove()
        if uncompressed_filepath and os.path.exists(uncompressed_filepath):
            _, _, _ = run_cmd("sudo -u uncompress rm -rf '{}'".format(uncompressed_filepath))


class ExcelImportFile(ImportFile):
    def __init__(self, file) -> None:
        super().__init__(file)
        self.valid_types = [
            "csv",
            "xlsx",
            "xls",
        ]
        self.filename, self.filetype = self._validate_filetype()


class MarkdownImportFile(ImportFile):
    def __init__(self, file) -> None:
        super().__init__(file)
        self.valid_types = [
            "md",
            "markdown",
        ]
        self.filename, self.filetype = self._validate_filetype()


class JsonImportFile(ImportFile):
    def __init__(self, file) -> None:
        super().__init__(file)
        self.valid_types = [
            "json"
        ]
        self.filename, self.filetype = self._validate_filetype()


@contextmanager
def file_concurrency_lock(lock_name, max_concurrency=2):
    current_key = str(uuid.uuid4())
    try:
        # 扫描过期key并删除
        current_timestamp = int(time.time())
        expired_members = redis_client.zrangebyscore(lock_name, 0, current_timestamp)
        for member in expired_members:
            redis_client.zrem(lock_name, member)

        concurrency = redis_client.zcard(lock_name)
        if concurrency and concurrency >= max_concurrency:
            yield False, jsonify(error_code=RET.BAD_REQ_ERR, error_msg='禁止连续请求文件接口，请稍后重试！')
        else:

            expire_time_in_seconds = 3 * 60
            timestamp = int(time.time()) + expire_time_in_seconds
            redis_client.zadd(lock_name, {current_key: timestamp})
            yield True, None
    finally:
        redis_client.zrem(lock_name, current_key)


def identify_file_type(file, need_type):
    try:
        # 禁止上传超大文件，文件头校验同时，保证文件在200M以内
        if file.content_length > 200 * 1024 * 1024:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="The file is too big, must be less than 500M!"
            )
        file_header = file.read(1024)
        # 文件指针恢复开始位置
        file.seek(0)
        file_type = magic.from_buffer(file_header, mime=True)
    except magic.MagicException as e:
        current_app.logger.error(f"无法识别文件类型: {e}")
        file_type = None

    if file_type in need_type:
        return True, None
    else:
        return False, jsonify(
            error_code=RET.BAD_REQ_ERR,
            error_msg="File header is not supported!"
        )


class FileTypeMapping(object):
    case_set_type = [
        "application/zip",
        "application/gzip",
        "application/x-gzip",
        "application/x-tar",
        "application/x-rar-compressed",
        "application/x-rar"
    ]
    test_case_type = [
        "text/plain",
        "text/markdown",
        "application/vnd.ms-excel",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]

    image_type = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/bmp",
        "image/x-ms-bmp",
        "image/x-windows-bmp",
        "image/svg+xml",
        "image/vnd.microsoft.icon",
        "image/x-icon"
    ]
    yaml_type = ["text/plain", "text/x-yaml", "application/yaml"]
