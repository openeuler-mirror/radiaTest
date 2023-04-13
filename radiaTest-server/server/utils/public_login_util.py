from server.model.user import User
from server.model.organization import Organization, ReUserOrganization
from server.model.group import Group, ReUserGroup
from server.utils.auth_util import generate_token
from server.utils.redis_util import RedisKey


def init_public_login(app, redis_client):
    """
    提供公共登录账户
    :param app: current app
    :param redis_client: redis客户端
    """
    with app.app_context():
        if not all((
            app.config.get("PUBLIC_USER_ID"),
            app.config.get("PUBLIC_USER_ACCOUNT"),
            app.config.get("PUBLIC_USER_ORG_NAME"),
            app.config.get("PUBLIC_TOKEN_EXPIRE_TIME")
        )):
            pass
        else:
            org = Organization.query.filter(
                Organization.name == app.config.get("PUBLIC_USER_ORG_NAME"),
                Organization.is_delete.is_(False)
            ).first()
            if not org:
                pass
            else:
                user_dict = {
                    'user_id': "gitee_{}".format(app.config.get("PUBLIC_USER_ID")),
                    'user_login': app.config.get("PUBLIC_USER_ACCOUNT"),
                    'user_name': app.config.get("PUBLIC_USER_NAME"),
                    'current_org_id': org.id
                }
                user = User.query.filter_by(user_id=user_dict.get("user_id")).first()
                if not user:
                    user = User()
                    user.user_id = "gitee_{}".format(app.config.get("PUBLIC_USER_ID"))
                    user.user_login = user_dict.get("user_login")
                    user.user_name = user_dict.get("user_name")
                    user.add_update()

                re_user_org = ReUserOrganization.query.filter_by(
                    user_id=user_dict.get("user_id"),
                    organization_id=org.id,
                    is_delete=False
                ).first()
                if not re_user_org:
                    re_user_org = ReUserOrganization()
                    re_user_org.user_id = user_dict.get("user_id")
                    re_user_org.organization_id = org.id
                    re_user_org.is_delete = False
                    re_user_org.default = True
                    re_user_org.add_update()

                group_name = app.config.get("PUBLIC_USER_GROUP")
                if group_name:
                    re_group = Group.query.filter_by(name=group_name, is_delete=False, org_id=org.id).first()
                    if re_group:
                        re_user_group = ReUserGroup.query.filter_by(
                            user_id=user_dict.get("user_id"),
                            group_id=re_group.id,
                            org_id=org.id,
                            is_delete=False,
                            user_add_group_flag=True
                        ).first()
                        if not re_user_group:
                            re_user_group = ReUserGroup()
                            re_user_group.user_id = user_dict.get("user_id")
                            re_user_group.group_id = re_group.id
                            re_user_group.org_id = org.id
                            re_user_group.is_delete = False
                            re_user_group.user_add_group_flag = True
                            re_user_group.role_type = 3
                            re_user_group.add_update()

                expire_time = int(app.config.get("PUBLIC_TOKEN_EXPIRE_TIME"))
                redis_client.hmset(RedisKey.user(user_dict.get('user_id')), user_dict, ex=expire_time)
                token = generate_token(
                    user_dict.get('user_id'),
                    user_dict.get('user_login'),
                    ex=expire_time
                )
                redis_client.set(RedisKey.token(user_dict.get('user_id')), token, ex=expire_time)

