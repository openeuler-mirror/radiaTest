from functools import wraps

from flask import jsonify, current_app
from flask_sqlalchemy import sqlalchemy
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .response_util import RET


def pdbc(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
            if ret:
                return ret
            return jsonify(
                {"error_code": 200, "error_mesg": "Request processed successfully."}
            )
        except sqlalchemy.exc.IntegrityError as e:
            current_app.logger.error(e)
            return jsonify(
                {
                    "error_code": 1001,
                    "error_mesg": "The submitted data has interleaving issues.",
                }
            )
        except ValueError as e:
            current_app.logger.error(e)
            return jsonify(
                {
                    "error_code": 1003,
                    "error_mesg": str(e),
                }
            )
        # except Exception as e:
        #     current_app.logger.error(e)
        #     return jsonify(
        #         {
        #             "error_code": 1009,
        #             "error_mesg": "Unknown error, please contact the administrator to handle.",
        #         }
        #     )

    return wrapper


def pdbc_filter(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            ret = func(*args, **kwargs)
            return ret
        except Exception as e:
            raise RuntimeError(e)

    return wrapper


class DataBase(object):
    @classmethod
    def method(cls, **kwargs):
        pass

    def __init__(self, table, data) -> None:
        self._table = table
        self._data = data


class FilterBase(DataBase):
    def __init__(self, table, data) -> None:
        super().__init__(table, data)
        self._filters = []
        for key, value in self._data.items():
            if hasattr(self._table, key):
                self._key = key
                self._value = value
                self.__class__.method(**self.__dict__)


class Precise(FilterBase):
    @classmethod
    def method(cls, **kwargs):
        if kwargs.get("_value"):
            return kwargs.get("_filters").append(
                getattr(kwargs.get("_table"), kwargs.get("_key"))
                == "{}".format(kwargs.get("_value"))
            )

    @pdbc_filter
    def all(self):
        if not self._filters:
            return self._table.query.all()
        return self._table.query.filter(*self._filters).all()

    @pdbc_filter
    def first(self):
        return self._table.query.filter(*self._filters).first()


class Like(Precise):
    @classmethod
    def method(cls, **kwargs):
        return kwargs.get("_filters").append(
            getattr(kwargs.get("_table"), kwargs.get("_key")).like(
                "%{}%".format(kwargs.get("_value"))
            )
        )


class MultipleConditions(Precise):
    @classmethod
    def method(cls, **kwargs):
        if not isinstance(kwargs.get("_value"), list):
            kwargs["_value"] = [kwargs.get("_value")]

        return kwargs.get("_filters").append(
            getattr(kwargs.get("_table"), kwargs.get("_key")).in_(kwargs.get("_value"))
        )


class Insert(FilterBase):
    @classmethod
    def method(cls, **kwargs):
        return setattr(
            kwargs.get("_instance"), kwargs.get("_key"), kwargs.get("_value")
        )

    def __init__(self, table, data: dict) -> None:
        self._instance = table()
        super().__init__(table, data)

    @pdbc
    def single(self, table, namespace):
        self._instance.add_update(table, namespace)

    def insert_id(self, table=None, namespace=None):
        return self._instance.add_flush_commit(table, namespace)


class Delete(DataBase):
    @pdbc
    def batch(self, table, namespace):
        data = MultipleConditions(self._table, self._data).all()
        if not data:
            raise ValueError("Related data has been deleted.")

        for d in data:
            d.delete(table, namespace)

    @pdbc
    def single(self, table, namespace):
        data = Precise(self._table, self._data).first()
        if not data:
            raise ValueError("Related data has been deleted.")

        data.delete(table, namespace)


class Edit(DataBase):
    @pdbc
    def single(self, Table=None, namespace=None):
        data = self._table.query.filter_by(id=self._data.get("id")).first()
        if not data:
            raise ValueError("Related data does not exist.")

        for key, value in self._data.items():
            if value != None:
                setattr(data, key, value)

        data.add_update(Table, namespace)

    @pdbc
    def pmachine(self, Table, namespace):
        data = self._table.query.filter_by(id=self._data.get("id")).first()
        if not data:
            raise ValueError("Related data does not exist.")

        for key, value in self._data.items():
            if value != "":
                setattr(data, key, value)

        data.add_update(Table, namespace)


class Select(DataBase):
    @pdbc
    def fuzz(self):
        return jsonify([data.to_json() for data in Like(self._table, self._data).all()])

    @pdbc
    def precise(self):
        return jsonify(
            [data.to_json() for data in Precise(self._table, self._data).all()]
        )


def collect_sql_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except IntegrityError as e:
            current_app.logger.error(f'database operate error -> {e}')
            return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg=f'data has exist / foreign key is bond')
        except SQLAlchemyError as e:
            current_app.logger.error(f'database operate error -> {e}')
            return jsonify(error_code=RET.DB_ERR, error_msg=f'database operate error -> {e}')

    return wrapper
