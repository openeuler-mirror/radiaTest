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
                {"error_code": RET.OK, "error_msg": "Request processed successfully."}
            )
        except sqlalchemy.exc.IntegrityError as e:
            current_app.logger.error(e)
            return jsonify(
                {
                    "error_code": RET.DB_DATA_ERR,
                    "error_msg": "The submitted data has interleaving issues.",
                }
            )
        except ValueError as e:
            current_app.logger.error(e)
            return jsonify(
                {
                    "error_code": RET.DB_DATA_ERR,
                    "error_msg": str(e),
                }
            )

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
    def single(self, table=None, namespace=None, broadcast=False):
        self._instance.add_update(table, namespace, broadcast)

    def insert_id(self, table=None, namespace=None, broadcast=False):
        return self._instance.add_flush_commit_id(table, namespace, broadcast)

    def insert_obj(self, table=None, namespace=None, broadcast=False):
        return self._instance.add_flush_commit(table, namespace, broadcast)


class Delete(DataBase):
    @pdbc
    def batch(self, table=None, namespace=None, broadcast=False):
        data = MultipleConditions(self._table, self._data).all()
        if not data:
            raise ValueError("Related data has been deleted.")

        for d in data:
            d.delete(table, namespace, broadcast)

    @pdbc
    def single(self, table=None, namespace=None, broadcast=False):
        data = Precise(self._table, self._data).first()
        if not data:
            raise ValueError("Related data has been deleted.")

        data.delete(table, namespace, broadcast)


class Edit(DataBase):
    @pdbc
    def single(self, table=None, namespace=None, broadcast=False):
        data = self._table.query.filter_by(id=self._data.get("id")).first()
        if not data:
            raise ValueError("Related data does not exist.")

        for key, value in self._data.items():
            if value is not None:
                setattr(data, key, value)

        data.add_update(table, namespace, broadcast)

    @pdbc
    def batch(self, table=None, namespace=None, broadcast=False):
        data = MultipleConditions(self._table, {"id": self._data.get("id")}).all()
        if not data:
            raise ValueError("Batch update data has been exist.")
        self._data.pop("id")
        for d in data:
            for key, value in self._data.items():
                if value is not None:
                    setattr(d, key, value)
            d.add_update(table, namespace, broadcast)

    @pdbc
    def batch_update_status(self, table=None, namespace=None, broadcast=False):
        data = self._table.query.filter(self._table.name.in_(self._data.get("domain"))).all()
        if not data:
            raise ValueError("Related data does not exist.")
        self._data.pop("domain")
        for d in data:
            for key, value in self._data.items():
                if value is not None:
                    setattr(d, key, value)
            if d.status in ["running", "shut off"]:
                d.add_update(table, namespace, broadcast)
            else:
                pass


class Select(DataBase):
    @pdbc
    def fuzz(self):
        data = [dt.to_json() for dt in Like(self._table, self._data).all()]
        return jsonify(
            {
                "error_code": RET.OK,
                "error_msg": "OK!",
                "data": data
            }
        )

    @pdbc
    def precise(self):
        data = [dt.to_json() for dt in Precise(self._table, self._data).all()]
        return jsonify(
            {
                "error_code": RET.OK,
                "error_msg": "OK!",
                "data": data
            }
        )

    @pdbc
    def single(self):
        tdata = self._table.query.filter_by(id=self._data.get("id")).first()
        data = dict()
        if tdata:
            data = tdata.to_json()
        return jsonify(
            {
                "error_code": RET.OK,
                "error_msg": "OK!",
                "data": data
            }
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
