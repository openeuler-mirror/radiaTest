from os import path, makedirs
from flask import current_app
from werkzeug.utils import secure_filename
from uuid import uuid1
import socket
from functools import lru_cache


class FileUtil(object):

    @staticmethod
    def flask_save_file(file_storage, file_path):
        if not file_storage or not file_path:
            return None
        try:
            file_path_temp = file_path.split(current_app.static_url_path, 1)[1]
            file_suffix = path.splitext(secure_filename(file_storage.filename))[-1]
            file_storage.save(f'{current_app.static_folder}{file_path_temp}{file_suffix}')
            return f'http://{get_local_ip()}:{current_app.config.get("NGINX_LISTEN")}' \
                   f'{current_app.static_url_path}{file_path_temp}{file_suffix}'.replace(path.sep, '/')
        except Exception as e:
            current_app.logger.error(f'file save error{e}')
        return None

    @staticmethod
    def generate_filepath(static_dir):
        file_save_dir = f'{current_app.static_folder}{path.sep}{static_dir}'
        if not path.exists(file_save_dir):
            makedirs(file_save_dir)
        return f'{current_app.static_url_path}{path.sep}{static_dir}{path.sep}{uuid1().hex}'


@lru_cache()
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    socket_name = s.getsockname()
    return socket_name[0]
