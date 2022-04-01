import os
import re
import socket
from uuid import uuid1
from shutil import rmtree
from shlex import quote
from functools import lru_cache
from werkzeug.utils import secure_filename

import zipfile
import rarfile
import tarfile
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
            return f'http://{get_local_ip()}:{current_app.config.get("NGINX_LISTEN")}' \
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
    def __init__(self, file) -> None:
        self.file = file
        self.filepath = None
        self.valid_types = [".+"]
        self.filename, self.filetype = self._validate_filetype()

    def _validate_filetype(self):
        pattern = r'^([^\.].*?)\.({})$'.format('|'.join(self.valid_types))
        result = re.search(pattern, self.file.filename)
        if not result:
            return None
        return result[1], result[2]
    
    def file_save(self, dir):
        self.filepath = os.path.join(
            dir, 
            secure_filename(
                ''.join(
                    lazy_pinyin("{}.{}".format(self.filename, self.filetype))
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
    
    def unicoding(self, name, dest_dir):
        try:
            os.rename(
                os.path.join(dest_dir, name), 
                os.path.join(
                    dest_dir, 
                    name.encode('cp437').decode('utf-8')
                )
            )
        except (UnicodeEncodeError, UnicodeDecodeError):
            try:
                os.rename(
                    os.path.join(dest_dir, name), 
                    os.path.join(
                        dest_dir, 
                        name.encode('gbk').decode('utf-8')
                    )
                )
            except (UnicodeEncodeError, UnicodeDecodeError):
                os.rename(
                    os.path.join(dest_dir, name), 
                    os.path.join(
                        dest_dir, 
                        name.encode('utf-8').decode('utf-8')
                    )
                )

    def uncompress(self, dest_dir):
        if self.filetype == 'zip':
            zip_file = zipfile.ZipFile(self.filepath)
            
            require_remove_origin = False

            for name in zip_file.namelist():
                # 过滤MAC OS压缩生成的缓存文件
                if self.macos_cache in name:
                    continue
                
                zip_file.extract(name, dest_dir)
                self.unicoding(name, dest_dir)
            
            if require_remove_origin:
                tmp_filepath = os.path.join(dest_dir, zip_file.namelist()[0])
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
            os.chdir(dest_dir)
            rar.extractall()
            rar.close()

        else:
            tar = tarfile.open(name=self.filepath, mode="r:*")
            for name in tar.getnames():
                tar.extract(name, dest_dir)
                self.unicoding(name, dest_dir)
            tar.close()


class ExcelImportFile(ImportFile):
    def __init__(self, file) -> None:
        super().__init__(file)
        self.valid_types = [
            "csv", 
            "xlsx", 
            "xls", 
        ]
