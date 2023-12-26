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
import socket
import datetime
from pathlib import Path
from uuid import uuid1
from shlex import quote
from functools import lru_cache
from werkzeug.utils import secure_filename

from flask import current_app
from pypinyin import lazy_pinyin

from server.utils.shell import local_cmd


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


@lru_cache()
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    socket_name = s.getsockname()
    return socket_name[0]


class ImportFile:
    def __init__(self, file, filename=None, filetype=None) -> None:
        self.file = file
        self.filepath = None
        self.valid_types = [".+"]
        self.filename=filename
        self.filetype=filetype
        if not filename and not filetype:
            self.filename, self.filetype = self._validate_filetype()

    def _validate_filetype(self):
        pattern = r'^([^\.].*?)\.({})$'.format('|'.join(self.valid_types))
        result = re.search(pattern, self.file.filename)
        if not result:
            return None
        return result[1], result[2]
    
    def file_save(self, dir, timestamp=True):
        if timestamp:
            self.filepath = os.path.join(
                dir, 
                secure_filename(
                    ''.join(
                        lazy_pinyin(
                            "{}.{}.{}".format(
                                self.filename, 
                                datetime.datetime.now().strftime("%Y%m%d%H%M%S"), 
                                self.filetype
                            )
                        )
                    )
                )
            )
        else:
            self.filepath = os.path.join(
                dir, 
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
        local_cmd(cmd)


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

    def uncompress(self, dist_dir):
        # 赋予uncompress解压目录权限
        local_cmd("chmod 777 '{}'".format(dist_dir))
        # 使用uncompress普通用户,安全解压
        safe_uncompress = Path(__file__).parent.joinpath("safe_uncompress.py")
        local_cmd("sudo -u uncompress python3 '{}' -t '{}' -f '{}' -d '{}'".format(
            safe_uncompress, self.filetype, self.filepath, dist_dir))


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
