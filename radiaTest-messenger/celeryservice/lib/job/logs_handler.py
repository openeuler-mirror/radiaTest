import os
import re
import requests
import tempfile

import wget
from flask.globals import current_app

from messenger.utils.requests_util import create_request, query_request, update_request
from messenger.utils.shell import ShellCmd
from messenger.utils.bash import rsync_password_file_delete, rsync_password_file_generator, rsync_dir_push


class LogsHandler:
    def __init__(self, conn, job_id, job_name, framework, adaptor, auth):
        self._conn = conn
        self._job_id = job_id
        self._job_name = job_name
        self._framework = framework
        self._adaptor = adaptor
        self._auth = auth
        self._logs_path = self._init_logs_path()

    def _init_logs_path(self):
        _path = ""
        if self._conn:
            _path = current_app.config.get(
                "WORKER_DOWNLOAD_PATH"
            ).replace("/$", "")
        else:
            _path = current_app.config.get(
                "SERVER_FRAMEWORK_PATH"
            ).replace("/$", "")

        return _path + '/' + self._framework.get("name") + '/' + self._framework.get("logs_path").replace("/$", "")

    def push_dir_to_server(self):
        # install rsync
        exitcode, output = ShellCmd(
            "which rsync || dnf install rsync -y",
            self._conn,
        )._exec()

        if exitcode:
            raise RuntimeError("Failed to install rsync.")

        # current_app.logger.info(output)

        # generate password file
        exitcode, output = ShellCmd(
            rsync_password_file_generator(),
            self._conn,
        )._exec()

        if exitcode:
            raise RuntimeError("Failed to generate password file for rsync.")

        # current_app.logger.info(output)

        # push logs by rsync
        exitcode, output = ShellCmd(
            rsync_dir_push(self._logs_path, self._job_name),
            self._conn,
        )._exec()

        if exitcode:
            raise RuntimeError("Failed to push logs by rsync.")

        # current_app.logger.info(output)

        # generate password file
        exitcode, output = ShellCmd(
            rsync_password_file_delete(),
            self._conn,
        )._exec()

        if exitcode:
            raise RuntimeError(
                "Failed to delete password file for rsync."
            )

    def loads_to_db(self, case_id):
        analyzed = query_request(
            "/api/v1/analyzed/preciseget",
            {
                "job_id": self._job_id,
                "case_id": case_id
            },
            self._auth,
        )
        if not analyzed:
            raise RuntimeError(
                "cannot update analyzed data, for it does not exist"
            )
        
        analyzed = analyzed[0]

        case = query_request(
            "/api/v1/case/preciseget",
            {
                "id": case_id
            },
            self._auth
        )
        if not case:
            raise RuntimeError("The relative case of the logs is not exist")
        case = case[0]

        _log_url = analyzed.get("log_url")

        _resp = requests.get(_log_url)
        if _resp.status_code != 200:
            raise RuntimeError(
                "Could not connect to the logs url: {}".format(_log_url)
            )

        _text = _resp.text
        _pattern = r'<a href="(.*)">.*\.log</a>'

        _logs_name = re.findall(_pattern, _text)[0].replace("./", "")

        tmpdir = tempfile.gettempdir()
        _log_file = wget.download(
            _log_url + _logs_name,
            out=os.path.join(tmpdir, "{}-{}-{}".format(
                self._job_name,
                case.get("name"),
                _logs_name
            )),
            bar=None,
        )

        with open(_log_file, 'r') as f:
            lines = f.read().splitlines()

            _log_data = self._adaptor.loads_logs(lines)

            logs = []
            for data in _log_data:
                log = create_request(
                    "/api/v1/log",
                    data,
                    self._auth
                )
                logs.append(log.get("id"))

            update_request(
                "/api/v1/analyzed/{}".format(
                    analyzed.get("id")
                ),
                {
                    "logs": logs
                },
                self._auth
            )

        if os.path.exists(_log_file):
            os.remove(_log_file)
