import configparser
from pathlib import Path

from flask import Flask


def loads_config_ini(app):
    if not isinstance(app, Flask) or not app.config.get("INI_PATH"):
        return False

    server_config_ini = Path(app.config.get("INI_PATH"))

    cfg = configparser.ConfigParser()
    cfg.read(server_config_ini)

    for section, _ in cfg.items():
        for key, value in cfg.items(section):
            try:
                _value = int(value)

            except ValueError as e:
                _value = value
            
            app.config[key.upper()] = _value

    return True
