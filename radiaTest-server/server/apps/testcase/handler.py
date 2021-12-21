import os
import re
from shlex import quote

from werkzeug.utils import secure_filename
from pypinyin import lazy_pinyin

from server.model.testcase import Suite
from server.utils.shell import local_cmd


class CaseFile:
    def __init__(self, form, files):
        self.form = form
        self.files = files
        self.filename = secure_filename(
            ''.join(lazy_pinyin(self.files.get("file").filename))
        )

    def checkSuiteValid(self):
        if not self.form.get("suite"):
            return False
        
        _suite = self.form.get("suite")
        if not Suite.query.filter_by(name=_suite).all():
            return False
        
        return True

    def getFiletype(self):
        if not self.files.get("file"):
            return None
        
        pattern = r'(?<=\.)(xlsx|xls|csv)$'
        
        result = re.search(pattern, self.filename)
        if not result:
            return None
        
        return result[0]
    
    def save(self, dir):
        self.file_path = os.path.join(dir, self.filename)
        self.files.get("file").save(self.file_path)
        return self.file_path

    def remove(self):
        cmd = "rm -f {}".format(quote(self.file_path))

        local_cmd(cmd)
