# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    :
# @License : Mulan PSL v2
#####################################

import yaml
import os
from server.model.permission import Scope
from server.model.administrator import Admin
from server.model.permission import Role
from server.model.alembic_version import AlembicVersion


def init_admin(db, app):
    with app.app_context():
        _admin = Admin.query.all()
        for _ in _admin:
            if not (_.account == app.config.get('ADMIN_USERNAME')
                    and Admin.check_password_hash(_, app.config.get('ADMIN_PASSWORD'))):
                db.session.delete(_)
                _admin.remove(_)
        db.session.commit()
        if not _admin:
            admin = Admin(account=app.config.get('ADMIN_USERNAME'), password=app.config.get('ADMIN_PASSWORD'))
            admin.add_flush_commit()


def init_scope(db, app):
    with app.app_context():
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base_dir, "config" + os.sep + "scope_init.yaml"), 'r', encoding='utf-8') as f:
            try:
                result = yaml.safe_load(f.read())
            except yaml.YAMLError as e:
                raise RuntimeError(e)
        eft_dict = {'allow': '允许', 'deny': '拒绝'}
        for scope in result:
            alias = scope['alias']
            uri = scope['uri']
            act = scope['act']
            for eft in eft_dict:
                new_alias = eft_dict[eft] + alias
                scope = Scope.query.filter_by(alias=new_alias).first()
                if scope and (scope.uri != uri or scope.act != act or scope.eft != eft):
                    scope.uri = uri
                    scope.act = act
                    scope.eft = eft
                    scope.add_update()
                if not scope:
                    scope = Scope(alias=new_alias, uri=uri, act=act, eft=eft)
                    db.session.add(scope)
            db.session.commit()


def init_role(db, app):
    with app.app_context():
        _role = Role.query.filter_by(name='admin', type='public').first()
        if not _role:
            role = Role(name='admin', type='public', necessary=True)
            role.add_flush_commit()
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base_dir, "config" + os.sep + "role_init.yaml"), 'r', encoding='utf-8') as f:
            try:
                result = yaml.safe_load(f.read())
            except yaml.YAMLError as e:
                raise RuntimeError(e)
        role_list = result['public']
        for role_type in role_list:
            if role_type == 'user':
                for _ in role_list[role_type]:
                    role = Role(name=_, type='public', necessary=True)
                    _role = Role.query.filter_by(name=_, type='public').first()
                    if not _role:
                        role.add_flush_commit()

            elif role_type == 'default':
                suffix = role_list[role_type]
                _role = Role.query.filter_by(name=suffix, type='public').first()
                if not _role:
                    _role = Role(name=suffix, type='public', necessary=True)
                    _role.add_flush_commit()
                public_roles = Role.query.filter(Role.type == 'public', Role.name != suffix).all()
                _origin = [_ for _ in _role.children]
                _ = [_role.children.append(item) for item in public_roles if item not in _role.children]
                _after = [_ for _ in _role.children]
                _role.add_update(difference=list(set(_after) - set(_origin)))


def create_role(_type, group=None, org=None):
    from flask import current_app
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base_dir, "config" + os.sep + "role_init.yaml"), 'r', encoding='utf-8') as f:
        try:
            result = yaml.safe_load(f.read())
        except yaml.YAMLError as e:
            current_app.logger.error(f'init role when creating org/group error -> {e}')
            raise RuntimeError(e)
    role_list = result[_type]
    admin_role = None
    return_list = []
    for role_type in role_list:
        if role_type != 'user':
            suffix = role_list[role_type]
            _filter = [Role.name == suffix, Role.type == _type, Role.org_id == org.id]
            _not_default_filter = [Role.name != suffix, Role.type == _type, Role.org_id == org.id]
            role = Role(name=suffix, type=_type, org_id=org.id, necessary=True)
            if _type == 'group':
                _filter.append(Role.group_id == group.id)
                _not_default_filter.append(Role.group_id == group.id)
                role.group_id = group.id
            _role = Role.query.filter(*_filter).first()
            if not _role:
                role.add_flush_commit()
                return_list.append(role)
                if role_type == 'administrator':
                    admin_role = role
                else:
                    # 角色继承
                    not_default_roles = Role.query.filter(*_not_default_filter).all()
                    _ = [role.children.append(item) for item in not_default_roles if item not in role.children]
                    role.add_update()
        else:
            _filter = [Role.type == _type, Role.org_id == org.id]
            role = Role(type=_type, org_id=org.id, necessary=True)
            if _type == 'group':
                _filter.append(Role.group_id == group.id)
                role.group_id = group.id
            for _ in role_list[role_type]:
                _filter_param = _filter.copy()
                _filter_param.append(Role.name == _)
                _role = Role.query.filter(*_filter_param).first()
                if not _role:
                    role.name = _
                    role.add_flush_commit()
                    return_list.append(role)

    return admin_role, return_list


def get_api(_path, file, matching_word, id):
    from flask import current_app
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base_dir, "apps" + os.sep + _path + os.sep + file), 'r', encoding='utf-8') as f:
        try:
            result = yaml.safe_load(f.read())
        except yaml.YAMLError as e:
            current_app.logger.error(f'get api error -> {e}')
            raise RuntimeError(e)
    allow_list = list()
    deny_list = list()
    _list = list()
    eft_dict = {'allow': '允许', 'deny': '拒绝'}
    for scope in result:
        for eft in eft_dict:
            _list.append({
                "alias": eft_dict[eft] + scope['alias'] + "_" + matching_word + "_" + str(id),
                "uri": str(scope['uri']).replace("{" + matching_word + "_id}", str(id)),
                "act": scope['act'],
                "eft": eft
            })

    for _ in _list:
        allow_list.append(_) if _['eft'] == 'allow' else deny_list.append(_)
    return allow_list, deny_list


def get_default_suffix(role_type):
    from flask import current_app
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base_dir, "config" + os.sep + "role_init.yaml"), 'r', encoding='utf-8') as f:
        try:
            result = yaml.safe_load(f.read())
        except yaml.YAMLError as e:
            current_app.logger.error(f'get_default_suffix error -> {e}')
            raise RuntimeError(e)
    role_list = result[role_type]
    suffix = None
    for role_type in role_list:
        if role_type == 'default':
            suffix = role_list[role_type]
    return suffix


def get_recv_id(db,app):
    with app.app_context():
        try:
            recv_version = AlembicVersion.query.first()
            version_num = recv_version.version_num
        except Exception as e:
            version_num=None
        if version_num:
            import os.path as op
            manage_file = op.join(op.dirname(op.dirname(op.dirname(op.abspath(__file__)))), 'manage.py')
            cmd = "python3 {} db revision --rev-id {}".format(manage_file, version_num)
            os.system(cmd)