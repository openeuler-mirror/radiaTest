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
from shutil import rmtree, move
from pathlib import Path

import rarfile


class SafeUncompress(object):
    def __init__(self, filetype, filepath):
        self.macos_cache = "__MACOSX"
        self.filetype = filetype
        self.filepath = Path(filepath).absolute()

    @staticmethod
    def unicoding(name, dist_dir):
        according = False

        try:
            new_name = name.encode('cp437').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            try:
                new_name = name.encode('gbk').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                new_name = name.encode('utf-8').decode('utf-8')
                according = True

        new_path = os.path.join(dist_dir, new_name)
        if name != new_name and os.path.isdir(new_path):
            rmtree(new_path)

        move(
            os.path.join(dist_dir, name),
            os.path.join(dist_dir, new_name)
        )

        return not according

    @staticmethod
    def is_safe_path(basedir, name):
        # resolves symbolic links
        path = basedir.joinpath(name)
        return os.path.abspath(path).startswith(str(basedir))

    def uncompress(self, dist_dir):
        dist_dir = Path(dist_dir).absolute()
        # 使用uncompress普通用户
        if self.filetype == 'zip':
            zip_file = zipfile.ZipFile(self.filepath)

            require_delete_origin = True

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
                zip_file.extract(name, dist_dir)

                require_delete_origin = self.unicoding(name, dist_dir)

            if require_delete_origin:
                tmp_filepath = os.path.join(dist_dir, zip_file.namelist()[0])
                try:
                    rmtree(tmp_filepath)
                except NotADirectoryError:
                    os.remove(tmp_filepath)
                    raise RuntimeError(
                        "zipped object should be a dictionary as importing case set"
                    )

            zip_file.close()

        elif self.filetype == 'rar':
            rar = rarfile.RarFile(self.filepath)
            for name in rar.namelist():
                if self.is_safe_path(dist_dir, name) is False:
                    continue
                rar.extract(name, dist_dir)
            rar.close()

        else:
            tar = tarfile.open(name=self.filepath, mode="r:*")
            for name in tar.getnames():
                info = tar.getmember(name).get_info()
                # 仅解压目录和普通文件
                if info.get("type") not in [b"0", b"5"] or info.get("linkname"):
                    continue
                # 安全检查过滤
                if self.is_safe_path(dist_dir, name) is False:
                    continue
                tar.extract(name, dist_dir)
                self.unicoding(name, dist_dir)
            tar.close()


def main():
    parser = argparse.ArgumentParser(description="安全解压压缩包至指定目录")
    parser.add_argument('-t', '--file_type', type=str, help="压缩包类型")
    parser.add_argument('-f', '--file', type=str, help="压缩包路径")
    parser.add_argument('-d', '--target_dir', type=str, help="解压目录")
    args = parser.parse_args()
    SafeUncompress(args.file_type, args.file).uncompress(args.target_dir)


if __name__ == '__main__':
    main()
