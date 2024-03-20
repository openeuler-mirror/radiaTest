# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : hukun66
# @email   : hu_kun@hoperun.com
# @Date    : 2023/11/24
# @License : Mulan PSL v2
#####################################
import argparse
import os
import re
import tarfile
import zipfile
from shutil import move
from pathlib import Path

from flask import current_app
import rarfile


class SafeUncompress(object):
    def __init__(self, filetype, filepath):
        self.macos_cache = "__MACOSX"
        self.filetype = filetype
        self.filepath = Path(filepath).absolute()
        self.dir_depth = 20  # 目录最大深度 20
        self.max_number = 1000  # 最大文件数 1000
        self.max_total_size = 100 * 1024 * 1024  # 最大空间占用量 100M

    @staticmethod
    def get_encoding_str(name):
        try:
            new_name = str(name).encode('cp437').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            try:
                new_name = str(name).encode('cp437').decode('gbk')
            except (UnicodeEncodeError, UnicodeDecodeError):
                try:
                    new_name = str(name).encode('gbk').decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    new_name = str(name).encode('utf-8').decode('utf-8')
        return new_name

    def unicoding(self, dist_dir, sub_dir=None):
        # 遍历目录进行乱码处理
        if not sub_dir:
            ord_path = dist_dir
            new_path = self.get_encoding_str(dist_dir)
        else:
            ord_path = os.path.join(dist_dir, sub_dir)
            new_path = os.path.join(dist_dir, self.get_encoding_str(sub_dir))
        if ord_path != new_path:
            move(ord_path, new_path)
        # 递归修改子目录
        if os.path.isdir(new_path):
            for sub_path in os.listdir(new_path):
                self.unicoding(new_path, sub_path)

    @staticmethod
    def is_safe_path(basedir, name):
        # resolves symbolic links
        path = basedir.joinpath(name)
        return os.path.abspath(path).startswith(str(basedir))

    def uncompress_zip(self, dist_dir):
        zip_file = zipfile.ZipFile(self.filepath)
        # 校验最大文件数
        if len(zip_file.namelist()) > self.max_number:
            current_app.logger.error("uncompress failed, files too many!")
            exit(1)
        safe_file_list = []
        total_size = 0
        for name in zip_file.namelist():
            # 过滤MAC OS压缩生成的缓存文件
            if self.macos_cache in name:
                continue
            # 安全检查过滤
            info = zip_file.getinfo(name)
            mode_ret = re.search("filemode='(?P<filemode>.+)'", str(info))
            # 仅解压目录和普通文件
            if mode_ret:
                if mode_ret.group("filemode")[0] not in ["-", "d"]:
                    continue
            if self.is_safe_path(dist_dir, name) is False:
                continue
            # 最大深度过滤
            path, _ = os.path.split(name)
            depth = len(path.split('/'))
            if depth > self.dir_depth:
                continue
            total_size += info.file_size
            safe_file_list.append(name)
        if total_size > self.max_total_size:
            current_app.logger.error("uncompress failed, total size too big!")
            exit(1)
        for safe_file in safe_file_list:
            zip_file.extract(safe_file, dist_dir)

        zip_file.close()

    def uncompress_rar(self, dist_dir):
        rar = rarfile.RarFile(self.filepath)
        if len(rar.namelist()) > self.max_number:
            current_app.logger.error("uncompress failed, files too many!")
            exit(1)
        safe_file_list = []
        total_size = 0
        for name in rar.namelist():
            if self.is_safe_path(dist_dir, name) is False:
                continue
            # 最大深度过滤
            path, _ = os.path.split(name)
            depth = len(path.split('/'))
            if depth > self.dir_depth:
                continue
            total_size += rar.getinfo(name).file_size
            safe_file_list.append(name)
        if total_size > self.max_total_size:
            current_app.logger.error("uncompress failed, total size too big!")
            exit(1)
        for safe_file in safe_file_list:
            rar.extract(safe_file, dist_dir)
        rar.close()

    def uncompress_tar(self, dist_dir):
        tar = tarfile.open(name=self.filepath, mode="r:*")
        if len(tar.getnames()) > self.max_number:
            current_app.logger.error("uncompress failed, files too many!")
            exit(1)
        safe_file_list = []
        total_size = 0
        for name in tar.getnames():
            info = tar.getmember(name).get_info()
            # 仅解压目录和普通文件
            if info.get("type") not in [b"0", b"5"] or info.get("linkname"):
                continue
            # 安全检查过滤
            if self.is_safe_path(dist_dir, name) is False:
                continue
            # 最大深度过滤
            path, _ = os.path.split(name)
            depth = len(path.split('/'))
            if depth > self.dir_depth:
                continue
            total_size += tar.getmember(name).size
            safe_file_list.append(name)

        if total_size > self.max_total_size:
            current_app.logger.error("uncompress failed, total size too big!")
            exit(1)
        for safe_file in safe_file_list:
            tar.extract(safe_file, dist_dir)
        tar.close()

    def uncompress(self, dist_dir):
        dist_dir = Path(dist_dir).absolute()
        if self.filetype == 'zip':
            self.uncompress_zip(dist_dir)
        elif self.filetype == 'rar':
            self.uncompress_rar(dist_dir)
        else:
            self.uncompress_tar(dist_dir)
        # 乱编码问题处理
        self.unicoding(str(dist_dir))


def main():
    parser = argparse.ArgumentParser(description="安全解压压缩包至指定目录")
    parser.add_argument('-t', '--file_type', type=str, help="压缩包类型")
    parser.add_argument('-f', '--file', type=str, help="压缩包路径")
    parser.add_argument('-d', '--target_dir', type=str, help="解压目录")
    args = parser.parse_args()
    SafeUncompress(args.file_type, args.file).uncompress(args.target_dir)


if __name__ == '__main__':
    main()
