import os
import re
from shutil import rmtree
from shlex import quote
from werkzeug.utils import secure_filename

from pypinyin import lazy_pinyin
import zipfile
import rarfile
import tarfile

from server.utils.shell import local_cmd


class ImportFile:
    def __init__(self, file) -> None:
        self.file = file
        self.filepath = None
        self.valid_types = [".+"]
        self.filename, self.filetype = self._validate_filetype()

    def _validate_filetype(self):
        pattern = r'^([^\.].*)\.({})$'.format('|'.join(self.valid_types))
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
            ".gz",
            ".xz",
            ".bz2",
            "tar.gz", 
            "tar.xz",
            "tar.bz2"
        ]
        self.macos_cache = "__MACOSX"

    def uncompress(self, dest_dir):
        if self.filetype == 'zip':
            zip_file = zipfile.ZipFile(self.filepath)

            for name in zip_file.namelist():
                # 过滤MAC OS压缩生成的缓存文件
                if self.macos_cache in name:
                    continue
                
                zip_file.extract(name, dest_dir)
                os.rename(
                    os.path.join(dest_dir, name), 
                    os.path.join(dest_dir, name.encode('cp437').decode('utf-8'))
                )
            
            rmtree(os.path.join(dest_dir, zip_file.namelist()[0]))
            zip_file.close()

        elif self.filetype == 'rar':
            rar = rarfile.RarFile(self.filepath)
            os.chdir(dest_dir)
            rar.extractall()
            rar.close()

        else:
            tar = tarfile.open(name=self.filepath)
            for name in tar.getnames():
                tar.extract(name, dest_dir)
            tar.close()


class ExcelImportFile(ImportFile):
    def __init__(self, file) -> None:
        super().__init__(file)
        self.valid_types = [
            "csv", 
            "xlsx", 
            "xls", 
        ]
    
