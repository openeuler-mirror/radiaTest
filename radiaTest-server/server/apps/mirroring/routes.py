from flask import request
from flask_restful import Resource
from flask_pydantic import validate


from server.utils.db import Insert, Delete, Edit, Select

from server.model import IMirroring, QMirroring, Repo

from server.schema.base import DeleteBaseModel
from server.schema.mirroring import (
    IMirroringBase,
    IMirroringUpdate,
    QMirroringBase,
    QMirroringUpdate,
    RepoCreate,
    RepoUpdate,
)


class IMirroringEvent(Resource):
    @validate()
    def post(self, body: IMirroringBase):
        return Insert(IMirroring, body.__dict__).single(IMirroring, '/imirroring')

    @validate()
    def delete(self, body: DeleteBaseModel):
        return Delete(IMirroring, body.__dict__).batch(IMirroring, '/imirroring')

    @validate()
    def put(self, body: IMirroringUpdate):
        return Edit(IMirroring, body.__dict__).single(IMirroring, '/imirroring')

    def get(self):
        body = request.args.to_dict()
        return Select(IMirroring, body).fuzz()


class PreciseGetIMirroring(Resource):
    def get(self):
        body = request.args.to_dict()
        return Select(IMirroring, body).precise()


class QMirroringEvent(Resource):
    @validate()
    def post(self, body: QMirroringBase):
        return Insert(QMirroring, body.__dict__).single(QMirroring, '/qmirroring')

    @validate()
    def delete(self, body: DeleteBaseModel):
        return Delete(QMirroring, body.__dict__).batch(QMirroring, '/qmirroring')

    @validate()
    def put(self, body: QMirroringUpdate):
        return Edit(QMirroring, body.__dict__).single(QMirroring, '/qmirroring')

    def get(self):
        body = request.args.to_dict()
        return Select(QMirroring, body).fuzz()


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
