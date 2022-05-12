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

from flask import request
from flask_restful import Resource
from flask_pydantic import validate


from server.utils.db import Insert, Delete, Edit, Select

from server.model.mirroring import IMirroring, QMirroring, Repo
from server.utils.resource_utils import ResourceManager
from server.schema.base import DeleteBaseModel
from server.schema.mirroring import (
    IMirroringBase,
    IMirroringUpdate,
    QMirroringBase,
    QMirroringUpdate,
    RepoCreate,
    RepoUpdate,
)

class IMirroringItemEvent(Resource):
    @validate()
    def delete(self, i_mirroring_id):
        return ResourceManager("i_mirroring").del_single(i_mirroring_id)

    @validate()
    def get(self, i_mirroring_id):
        return Select(IMirroring, {"id":i_mirroring_id}).single()

    @validate()
    def put(self, i_mirroring_id, body: IMirroringUpdate):
        _body = body.__dict__
        _body.update({"id": i_mirroring_id})
        return Edit(IMirroring, _body).single(IMirroring, '/imirroring')

class IMirroringEvent(Resource):
    @validate()
    def post(self, body: IMirroringBase):
        return Insert(IMirroring, body.__dict__).single(IMirroring, '/imirroring')

class PreciseGetIMirroring(Resource):
    def get(self):
        body = request.args.to_dict()
        return Select(IMirroring, body).precise()

class QMirroringItemEvent(Resource):
    @validate()
    def delete(self, q_mirroring_id):
        return ResourceManager("q_mirroring").del_single(q_mirroring_id)

    @validate()
    def get(self, q_mirroring_id):
        return Select(QMirroring, {"id":q_mirroring_id}).single()

    @validate()
    def put(self, q_mirroring_id, body: QMirroringUpdate):
        _body = body.__dict__
        _body.update({"id": q_mirroring_id})
        return Edit(QMirroring, _body).single(QMirroring, '/qmirroring')

class QMirroringEvent(Resource):
    @validate()
    def post(self, body: QMirroringBase):
        return Insert(QMirroring, body.__dict__).single(QMirroring, '/qmirroring')

class PreciseGetQMirroring(Resource):
    def get(self):
        body = request.args.to_dict()
        return Select(QMirroring, body).precise()


class RepoEvent(Resource):
    @validate()
    def post(self, body: RepoCreate):
        return Insert(Repo, body.__dict__).single(Repo, '/repo')

    @validate()
    def delete(self, body: DeleteBaseModel):
        return Delete(Repo, body.__dict__).batch(Repo, '/repo')

    @validate()
    def put(self, body: RepoUpdate):
        return Edit(Repo, body.__dict__).single(Repo, '/repo')

    def get(self):
        body = request.args.to_dict()
        return Select(Repo, body).fuzz()
