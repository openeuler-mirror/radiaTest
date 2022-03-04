import configparser
from pathlib import Path

from flask import Flask


def loads_config_ini(app):
    if not isinstance(app, Flask) or not app.config.get("CONFIG_INI_FILE_PATH"):
        return False

    config_ini = Path(app.config.get("CONFIG_INI_FILE_PATH"))

    cfg = configparser.ConfigParser()
    cfg.read(config_ini)

    for section, _ in cfg.items():
        for key, value in cfg.items(section):
            try:
                _value = int(value)

            except ValueError as e:
                _value = value
            
            app.config[key.upper()] = _value

    return True


def loads_db_url(file_path):
    cfg = configparser.ConfigParser()

    try:
        cfg.read(file_path)

        return cfg.get("database", "SQLALCHEMY_DATABASE_URI")

    except:
        
        return None