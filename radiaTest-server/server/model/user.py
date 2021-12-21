from server.model.base import Base
from server import db, redis_client
from server.utils.redis_util import RedisKey


class User(db.Model, Base):
    __tablename__ = "user"
    gitee_id = db.Column(db.Integer, primary_key=True)
    gitee_login = db.Column(db.String(50), nullable=False)
    gitee_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=True, default=None)
    avatar_url = db.Column(db.String(512), nullable=True, default=None)
    cla_email = db.Column(db.String(128), nullable=True, default=None)

    re_user_group = db.relationship("ReUserGroup", backref="user")
    re_user_organization = db.relationship("ReUserOrganization", backref="user")

    def to_dict(self):
        return {
            "gitee_id": self.gitee_id,
            "gitee_login": self.gitee_login,
            "gitee_name": self.gitee_name,
            "phone": self.phone,
            "avatar_url": self.avatar_url,
            "cla_email": self.cla_email,
        }

    @staticmethod
    def synchronize_gitee_info(gitee_user, user=None):
        user.gitee_login = gitee_user.get("login")
        user.gitee_name = gitee_user.get("name")
        user.avatar_url = gitee_user.get("avatar_url")
        user.add_update()
        return user

    def save_redis(self, access_token, refresh_token, current_org_id=None):
        redis_data = self.to_dict()
        redis_data['gitee_access_token'] = access_token
        redis_data['gitee_refresh_token'] = refresh_token
        if current_org_id:
            redis_data['current_org_id'] = current_org_id
        else:
            for item in self.re_user_organization:
                if item.default is True:
                    redis_data['current_org_id'] = item.organization_id
                    redis_data['current_org_name'] = item.organization.name
        redis_client.hmset(RedisKey.user(self.gitee_id), redis_data)

    @staticmethod
    def create_commit(gitee_user, cla_email=None, re_user_organization=None):
        new_user = User()
        new_user.gitee_id = gitee_user.get("id")
        new_user.gitee_login = gitee_user.get("login")
        new_user.gitee_name = gitee_user.get("name")
        new_user.avatar_url = gitee_user.get("avatar_url")
        new_user.cla_email = cla_email
        new_user.re_user_organization = re_user_organization
        new_user.add_update()
        return new_user
