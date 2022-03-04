from werkzeug.security import generate_password_hash, check_password_hash
from server.model.base import Base
from server import db, casbin_enforcer


class Admin(db.Model, Base):
    __tablename__ = 'administrator'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    account = db.Column(db.String(30), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    @property
    def password(self):
        raise AttributeError('password is not allowed reading')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password_hash(self, password):
        return check_password_hash(self.password_hash, password)

    def add_update(self, table=None, namespace=None):
        casbin_enforcer.adapter.add_policy(
            "g", 
            "g", 
            ["admin_%s"%(self.id), "root"]
        )
        return super().add_update(table, namespace)

    def delete(self, table, namespace):
        casbin_enforcer.adapter.remove_policy(
            "g", 
            "g", 
            ["admin_%s"%(self.id), "root"]
        )
        return super().delete(table, namespace)
