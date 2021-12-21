import json
from flask import request, g, jsonify
from sqlalchemy import or_
from server import redis_client
from server.model.organization import Organization, ReUserOrganization
from server.model.user import User
from server.model.group import ReUserGroup
from server.utils.response_util import RET
from server.utils.page_util import PageUtil
from server.utils.db import collect_sql_error
from server.utils.redis_util import RedisKey
from server.utils.cla_util import ClaShowUserSchema, Cla, ClaShowAdminSchema
from server.schema.organization import ReUserOrgSchema
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
    re = ReUserOrganization.query.filter_by(is_delete=False, user_gitee_id=g.gitee_id, organization_id=org_id).first()
    if re:
        return jsonify(error_code=RET.DATA_EXIST_ERR, error_msg="relationship has exist")
    # 从数据库中获取cla信息
    org = Organization.query.filter_by(id=org_id, is_delete=False).first()
    if not org:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg=f"database no find data")
    org_info = org.to_dict()
    if not Cla.is_cla_signed(ClaShowAdminSchema(**org_info).dict(), body.cla_verify_params, body.cla_verify_body):
        return jsonify(error_code=RET.CLA_VERIFY_ERR, error_msg="user is not pass cla verification, please retry",
                    data=g.gitee_id)
    # 生成用户和组织的关系
    ReUserOrganization.create(g.gitee_id, org_id,
                              json.dumps({**body.cla_verify_params, **body.cla_verify_body}),
                              default=False).add_update()
    return jsonify(error_code=RET.OK, error_msg="OK")


@collect_sql_error
def handler_org_user_page(org_id):
    page_num = int(request.args.get('page_num', 1))
    page_size = int(request.args.get('page_size', 10))
    name = request.args.get('name')
    group_id = request.args.get('group_id')
    # 判断当前用户是否属于该组织
    re = ReUserOrganization.query.filter_by(is_delete=False, user_gitee_id=g.gitee_id,
                                            organization_id=org_id).first()
    if not re or re.organization.is_delete:
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg="user organization no find")
    # 获取组织下的所有用户
    filter_params = [
        ReUserOrganization.is_delete == False,
        ReUserOrganization.organization_id == org_id,
        Organization.is_delete == False
    ]
    if group_id:
        re_u_g = ReUserGroup.query.filter_by(is_delete=False, group_id=group_id).all()
        user_gitee_ids = [item.user.gitee_id for item in re_u_g]
        filter_params.append(ReUserOrganization.user_gitee_id.notin_(user_gitee_ids))
    if name:
        filter_params.append(or_(User.gitee_name.like(f'%{name}%'), User.gitee_login.like(f'%{name}%')))

    query_filter = ReUserOrganization.query.join(Organization).join(User).filter(*filter_params)

    def page_func(item):
        re_dict = ReUserOrgSchema(**item.to_dict()).dict()
        user_dict = UserBaseSchema(**item.user.to_dict()).dict()
        return {**user_dict, **re_dict}

    # 返回结果
    page_dict, e = PageUtil.get_page_dict(query_filter, page_num, page_size, func=page_func)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get group page error {e}')
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)


@collect_sql_error
def handler_org_group_page(org_id, query: PageBaseSchema):
    if org_id != int(redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')):
        return jsonify(error_code=RET.NO_DATA_ERR, error_msg="user organization no find")
    query_filter = ReUserGroup.query.filter_by(is_delete=False, org_id=org_id)

    def page_func(item):
        return GroupInfoSchema(**item.group.__dict__).dict()

    # 返回结果
    page_dict, e = PageUtil.get_page_dict(query_filter, query.page_num, query.page_size, func=page_func, is_set=True)
    if e:
        return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get group page error {e}')
    return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)
