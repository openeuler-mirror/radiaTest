import os
import re
import requests
import tempfile

import wget
from flask.globals import current_app

from server.model.job import Analyzed, Logs
from server.model.testcase import Case
from server.utils.shell import ShellCmd
from server.utils.db import Insert
from server.utils.bash import rsync_password_file_delete, rsync_password_file_generator, rsync_dir_push


class LogsHandler:
    def __init__(self, conn, job_id, job_name, framework):
        self._conn = conn
        self._job_id = job_id
        self._job_name = job_name
        self._framework = framework
        self._logs_path = self._init_logs_path()

    def _init_logs_path(self):
        _path = ""
        if self._conn:
            _path = current_app.config.get(
                "TEST_MACHINE_FRAMEWORK_PATH"
            ).replace("/$", "")
        else:
            _path = current_app.config.get(
                "SERVER_FRAMEWORK_PATH"
            ).replace("/$", "")
        
        return _path + self._framework.logs_path.replace("/$", "")

    def push_dir_to_server(self):
        # install rsync
        exitcode, output = ShellCmd(
            "which rsync || dnf install rsync -y",
            self._conn,
        )._exec()

        if exitcode:
            raise RuntimeError("Failed to install rsync.")

        current_app.logger.info(output)

        # generate password file
        exitcode, output = ShellCmd(
            rsync_password_file_generator(),
            self._conn,
        )._exec()

        if exitcode:
            raise RuntimeError("Failed to generate password file for rsync.")

        current_app.logger.info(output)

        # push logs by rsync
        exitcode, output = ShellCmd(
            rsync_dir_push(self._logs_path, self._job_name),
            self._conn,
        )._exec()

        if exitcode:
            raise RuntimeError("Failed to push logs by rsync.")

        current_app.logger.info(output)

        # generate password file
        exitcode, output = ShellCmd(
            rsync_password_file_delete(),
            self._conn,
        )._exec()

        if exitcode:
            current_app.logger.warn("Failed to delete password file for rsync.")

    def loads_to_db(self, case_id):
        analyzed = Analyzed.query.filter_by(
            job_id=self._job_id, 
            case_id=case_id
        ).first()
        if not analyzed:
            raise RuntimeError("Could not load logs file before analysis")

        case = Case.query.filter_by(id=case_id).first()   
        if not case:
            raise RuntimeError("The relative case of the logs is not exist")
        
        _log_url = analyzed.log_url

        _resp = requests.get(_log_url)
        if _resp.status_code != 200:
            raise RuntimeError("Could not connect the repo server of logs")

        _text = _resp.text
        _pattern = r'<a href="(.*)">.*\.log</a>'

        _logs_name = re.findall(_pattern, _text)[0].replace("./", "")

        tmpdir = tempfile.gettempdir()
        _log_file = wget.download(
            _log_url + _logs_name, 
            out=os.path.join(tmpdir, "{}-{}-{}".format(
                self._job_name, 
                case.name, 
                _logs_name
            ))
        )

        with open(_log_file, 'r') as f:
            lines = f.read().splitlines()

            _log_data = self._framework.loads_logs(lines)

            for data in _log_data:
                log_id = Insert(Logs, data).insert_id()

                log = Logs.query.filter_by(id=log_id).first()

                analyzed.logs.append(log)
                
        if os.path.exists(_log_file):
            os.remove(_log_file)
