from server import db
from server.model import BaseModel


class CasbinRule(db.Model, BaseModel):
    __tablename__ = "casbin_rule"

    id = db.Column(db.Integer, primary_key=True)
    ptype = db.Column(db.String(255))
    v0 = db.Column(db.String(255))
    v1 = db.Column(db.String(255))
    v2 = db.Column(db.String(255))
    v3 = db.Column(db.String(255))
    v4 = db.Column(db.String(255))
    v5 = db.Column(db.String(255))

    def __str__(self):
        arr = [self.ptype]
        for v in (self.v0, self.v1, self.v2, self.v3, self.v4, self.v5):
            if v is None:
                break
            arr.append(v)
        return ", ".join(arr)

    def __repr__(self):
        return '<CasbinRule {}: "{}">'.format(self.id, str(self))