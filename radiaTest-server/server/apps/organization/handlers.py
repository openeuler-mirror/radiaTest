import json
from flask import request, g, jsonify
from sqlalchemy import or_
from server import redis_client
from server.model.organization import Organization, ReUserOrganization
from server.model.user import User
from server.model.group import Group, ReUserGroup
from server.model.permission import Role, ReUserRole
from server.utils.response_util import RET
from server.utils.page_util import PageUtil
from server.utils.db import collect_sql_error, Insert
from server.utils.redis_util import RedisKey
from server.utils.cla_util import ClaShowUserSchema, Cla, ClaShowAdminSchema
from server.utils.read_from_yaml import get_default_suffix
from server.schema.organization import OrgBaseSchema, ReUserOrgSchema
from server.schema.user import UserBaseSchema
from server.schema.base import PageBaseSchema
from server.schema.group import GroupInfoSchema


@collect_sql_error
def handler_show_org_cla_list():
    has_org_ids = [item.strip() for item in request.args.get('has_org_ids', '').split(',') if item]
    # 从数据库中获取数据
    org_list = Organization.query.filter_by(is_delete=False).all()
    # 提取cla信息
    cla_info_list = list()
    for item in org_list:
        if str(item.id) not in has_org_ids:
            cla_info_list.append(ClaShowUserSchema(**item.to_dict()).dict())
    return jsonify(error_code=RET.OK, error_msg="OK", data=cla_info_list)


@collect_sql_error
def handler_org_cla(org_id, body):
    re = ReUserOrganization.query.filter_by(
        is_delete=False,
        user_id=g.user_id,
        organization_id=org_id
    ).first()
    if re:
        return jsonify(
            error_code=RET.DATA_EXIST_ERR,
            error_msg="relationship has already existed"
        )

    # 从数据库中获取cla信息
    org = Organization.query.filter_by(id=org_id, is_delete=False).first()
    if not org:
        return jsonify(
            error_code=RET.NO_DATA_ERR,
            error_msg=f"the organization does not exist"
        )

    org_info = org.to_dict()

    if org.cla_verify_url and not Cla.is_cla_signed(
        ClaShowAdminSchema(**org_info).dict(),
        body.cla_verify_params,
        body.cla_verify_body
    ):
        return jsonify(
            error_code=RET.CLA_VERIFY_ERR,
            error_msg="the user does not pass cla verification, please retry",
            data=g.user_id
        )

    # 生成用户和组织的关系
    ReUserOrganization.create(
        g.user_id,
        org_id,
        json.dumps({**body.cla_verify_params, **body.cla_verify_body}),
        default=False
    ).add_update()

    # 绑定用户和组织基础角色
    org_suffix = get_default_suffix('org')
    filter_params = [
        Role.org_id == org_id,
        Role.type == 'org',
        Role.name == org_suffix
    ]
    _role = Role.query.filter(*filter_params).first()
    Insert(ReUserRole, {"user_id": g.user_id, "role_id": _role.id}).single()

    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_org_user_page(org_id):
    page_num = int(request.args.get('page_num', 1))
    page_size = int(request.args.get('page_size', 10))
    name = request.args.get('name')
    group_id = request.args.get('group_id')

    # 获取组织下的所有用户
    filter_params = [
        ReUserOrganization.is_delete == False,
        ReUserOrganization.organization_id == org_id,
        Organization.is_delete == False
    ]
    if group_id:
        re_u_g = ReUserGroup.query.filter_by(is_delete=False, group_id=group_id).all()
        user_ids = [item.user.user_id for item in re_u_g]
        filter_params.append(ReUserOrganization.user_id.notin_(user_ids))
    if name:
        filter_params.append(or_(User.user_name.like(f'%{name}%'), User.user_login.like(f'%{name}%')))

    query_filter = ReUserOrganization.query.join(Organization).join(User).filter(*filter_params)

    def page_func(item):
        re_dict = ReUserOrgSchema(**item.to_dict()).dict()
        user_dict = item.user.to_dict()
        return {**user_dict, **re_dict}

    # 返回结果
    page_dict, e = PageUtil.get_page_dict(query_filter, page_num, page_size, func=page_func)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get group page error {e}')
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


@collect_sql_error
def handler_org_group_page(org_id, query: PageBaseSchema):

    query_filter = ReUserGroup.query.join(Group).filter(
        ReUserGroup.is_delete == False,
        Group.is_delete == False,
        ReUserGroup.org_id == org_id,
    ).order_by(ReUserGroup.create_time)

    def page_func(item):
        return GroupInfoSchema(**item.group.to_dict()).dict()

    # 返回结果
    page_dict, e = PageUtil.get_page_dict(query_filter, query.page_num, query.page_size, func=page_func, is_set=True)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get group page error {e}')
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


@collect_sql_error
def handler_get_all_org(query):
    filter_params = [
        Organization.is_delete == query.is_delete,
    ]
    if query.org_name:
        filter_params.append(Organization.name.like(f'%{query.org_name}%'))
    if query.org_description:
        filter_params.append(Organization.description.like(f'%{query.org_description}%'))

    query_filter = Organization.query.filter(*filter_params)

    def page_func(item):
        if item.is_delete:
            return None
        return OrgBaseSchema(**item.to_dict()).dict()

    page_dict, e = PageUtil.get_page_dict(query_filter, query.page_num, query.page_size, func=page_func)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get organization page error {e}')

    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


@collect_sql_error
def handler_org_statistic(org_id: int):
    total_groups = Group.query.filter_by(org_id=org_id, is_delete=False).count()
    total_users = ReUserOrganization.query.filter_by(organization_id=org_id, is_delete=False).count()

    return jsonify(
        error_code=RET.OK,
        error_msg="OK",
        data={
            "total_groups": total_groups,
            "total_users": total_users,
        }
    ) 