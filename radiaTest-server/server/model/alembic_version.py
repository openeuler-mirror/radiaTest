from server import db

class AlembicVersion(db.Model):
    __tablename__ = 'alembic_version'
    version_num = db.Column(db.String(32), primary_key=True)

    def to_dict(self):
        return {
            'version_num': self.version_num
        }

    def to_json(self):
        return {
            "version_num": self.version_num
        }