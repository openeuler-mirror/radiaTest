import os
import re
import shutil

from flask import jsonify, g, current_app, request

from server import db, redis_client
from server.utils.redis_util import RedisKey
from server.utils.response_util import RET
from server.utils.db import Edit, Insert, collect_sql_error
from server.model.testcase import Baseline, Suite, Case
from server.model.celerytask import CeleryTask
from server.schema.testcase import BaselineBaseSchema
from server.schema.celerytask import CeleryTaskUserInfoSchema
from server.utils.files_util import ZipImportFile, ExcelImportFile
from server.utils.sheet import Excel, SheetExtractor
from celeryservice.tasks import resolve_testcase_file, resolve_testcase_file_for_baseline, resolve_testcase_set


class CaseImportHandler:
    @staticmethod
    @collect_sql_error
    def loads_data(filetype, filepath, group_id):
        excel = Excel(filetype).load(filepath)

        cases = SheetExtractor(
            current_app.config.get("OE_QA_TESTCASE_DICT")
        ).run(excel)

        suites = set()

        for case in cases:
            if not case.get("name") or not case.get("suite") or not case.get("steps") or not case.get("expection") or not case.get("description"):
                continue

            if case.get("automatic") == '是' or case.get("automatic") == 'Y':
                case["automatic"] = True
            else:
                case["automatic"] = False

            _case = Case.query.filter_by(name=case.get("name")).first()

            _suite = Suite.query.filter_by(
                name=case.get("suite")
            ).first()
            if not _suite:
                Insert(
                    Suite,
                    {
                        "name": case.get("suite"),
                        "group_id": group_id,
                        "org_id": redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id'),
                    }
                ).single(Suite, '/suite')
                _suite = Suite.query.filter_by(
                    name=case.get("suite")
                ).first()

            case["suite_id"] = _suite.id

            suites.add(_suite.id)

            del case["suite"]

            if not _case:
                Insert(Case, case).single(Case, "/case")

                _case = Case.query.filter_by(name=case.get("name")).first()
            else:
                case["id"] = _case.id

                Edit(Case, case).single(Case, "/case")

        return suites

    @staticmethod
    @collect_sql_error
    def import_case(file, group_id, baseline_id=None):
        try:
            case_file = ExcelImportFile(file)

            if case_file.filetype:
                case_file.file_save(
                    current_app.config.get("UPLOAD_FILE_SAVE_PATH")
                )

                _task = None

                if baseline_id is not None:
                    _task = resolve_testcase_file_for_baseline.delay(
                        baseline_id,
                        case_file.filepath,
                        CeleryTaskUserInfoSchema(
                            auth=request.headers.get("authorization"),
                            user_id=int(g.gitee_id),
                            group_id=group_id,
                            org_id=redis_client.hget(
                                RedisKey.user(g.gitee_id),
                                'current_org_id'
                            )
                        ).__dict__,
                    )
                else:
                    _task = resolve_testcase_file.delay(
                        case_file.filepath,
                        CeleryTaskUserInfoSchema(
                            auth=request.headers.get("authorization"),
                            user_id=int(g.gitee_id),
                            group_id=group_id,
                            org_id=redis_client.hget(
                                RedisKey.user(g.gitee_id),
                                'current_org_id'
                            )
                        ).__dict__,
                    )

                if not _task:
                    return jsonify(error_code=RET.SERVER_ERR, error_msg="could not send task to resolve file")

                _ = Insert(
                    CeleryTask,
                    {
                        "tid": _task.task_id,
                        "status": "PENDING",
                        "object_type": "testcase_resolve",
                        "description": f"resolve testcase {case_file.filepath}",
                        "user_id": int(g.gitee_id)
                    }
                ).single(CeleryTask, '/celerytask')

                return jsonify(error_code=RET.OK, error_msg="OK")

            else:
                mesg = "Filetype of {}.{} is not supported".format(
                    case_file.filename,
                    case_file.filetype,
                )

                current_app.logger.error(mesg)

                if os.path.exists(case_file.filepath):
                    case_file.file_remove()

                return jsonify(error_code=RET.OK, error_msg=mesg)

        except RuntimeError as e:
            current_app.logger.error(str(e))

            if os.path.exists(case_file.filepath):
                case_file.file_remove()

            return jsonify(error_code=RET.SERVER_ERR, error_msg=str(e))


class BaselineHandler:
    @staticmethod
    @collect_sql_error
    def get(baseline_id, query):
        baseline = Baseline.query.filter_by(id=baseline_id).first()

        if not baseline:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="baseline is not exists")

        current_org_id = int(redis_client.hget(
            RedisKey.user(g.gitee_id),
            'current_org_id'
        ))

        if current_org_id != baseline.org_id:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="No right to query")

        return_data = BaselineBaseSchema(**baseline.__dict__).dict()

        filter_params = [Baseline.parent.contains(baseline)]

        for key, value in query.dict().items():
            if not value:
                continue
            if key == 'title':
                filter_params.append(Baseline.title.like(f'%{value}%'))

        children = Baseline.query.filter(*filter_params).all()

        return_data["children"] = [child.to_json() for child in children]

        source = list()
        cur = baseline

        while cur:
            if not cur.parent.all():
                source.append(cur.id)
                break
            if len(cur.parent.all()) > 1:
                raise RuntimeError(
                    "baseline should not have parents beyond one")

            source.append(cur.id)
            cur = cur.parent[0]

        return_data["source"] = source

        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def get_roots(query):
        filter_params = [
            Baseline.is_root.is_(True),
            Baseline.org_id == redis_client.hget(
                RedisKey.user(g.gitee_id), 'current_org_id'),
            Baseline.group_id == query.group_id,
        ]
        for key, value in query.dict().items():
            if not value:
                continue
            if key == 'title':
                filter_params.append(Baseline.title.like(f'%{value}%'))

        baselines = Baseline.query.filter(*filter_params).all()
        return_data = [baseline.to_json() for baseline in baselines]
        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def create(body):
        _body = body.__dict__
        _body["org_id"] = redis_client.hget(
            RedisKey.user(g.gitee_id), 'current_org_id')

        if not body.parent_id:
            baseline_id = Insert(Baseline, body.__dict__).insert_id()
            return jsonify(error_code=RET.OK, error_msg="OK", data=baseline_id)

        parent = Baseline.query.filter_by(id=body.parent_id).first()
        if not parent:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="parent node is not exists")

        for child in parent.children:
            if _body["title"] == child.title:
                return jsonify(
                    error_code=RET.OK,
                    error_msg="Title {} is already exist".format(
                        _body["title"]
                    ),
                    data=child.id
                )

        baseline = Baseline.query.filter_by(
            id=Insert(
                Baseline,
                body.__dict__
            ).insert_id()
        ).first()

        baseline.parent.append(parent)
        baseline.add_update()

        return jsonify(error_code=RET.OK, error_msg="OK", data=baseline.id)

    @staticmethod
    @collect_sql_error
    def update(baseline_id, body):
        baseline = Baseline.query.filter_by(id=baseline_id).first()

        current_org_id = int(
            redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        )

        if current_org_id != baseline.org_id:
            return jsonify(error_code=RET.VERIFY_ERROR, error_msg="No right to edit")

        if not baseline:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="baseline is not exists")

        baseline.title = body.title

        baseline.add_update()

        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def delete(baseline_id):
        baseline = Baseline.query.filter_by(id=baseline_id).first()

        current_org_id = int(
            redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
        )

        if current_org_id != baseline.org_id:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="No right to delete")

        if not baseline:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="baseline is not exists")

        db.session.delete(baseline)
        db.session.commit()

        return jsonify(error_code=RET.OK, error_msg="OK")

    @staticmethod
    @collect_sql_error
    def import_case_set(file, group_id):
        uncompressed_filepath = None
        try:
            zip_case_set = ZipImportFile(file)

            if zip_case_set.filetype:
                zip_case_set.file_save(
                    current_app.config.get("UPLOAD_FILE_SAVE_PATH")
                )

                uncompressed_filepath = "{}/{}".format(
                    os.path.dirname(zip_case_set.filepath),
                    zip_case_set.filename
                )

                zip_case_set.uncompress(os.path.dirname(zip_case_set.filepath))

                _task = resolve_testcase_set.delay(
                    zip_case_set.filepath,
                    uncompressed_filepath,
                    CeleryTaskUserInfoSchema(
                        auth=request.headers.get("authorization"),
                        user_id=int(g.gitee_id),
                        group_id=group_id,
                        org_id=redis_client.hget(
                            RedisKey.user(g.gitee_id),
                            'current_org_id'
                        )
                    ).__dict__,
                )

                _ = Insert(
                    CeleryTask,
                    {
                        "tid": _task.task_id,
                        "status": "PENDING",
                        "object_type": "caseset_resolve",
                        "description": "Import a set of testcases",
                        "user_id": int(g.gitee_id)
                    }
                ).single(CeleryTask, '/celerytask')

                return jsonify(error_code=RET.OK, error_msg="OK")

            else:
                if os.path.exists(zip_case_set.filepath):
                    zip_case_set.file_remove()
                if uncompressed_filepath and os.path.exists(uncompressed_filepath):
                    shutil.rmtree(uncompressed_filepath)

                return jsonify(error_code=RET.FILE_ERR, error_msg="filetype is not supported")

        except RuntimeError as e:
            current_app.logger.error(str(e))

            if os.path.exists(zip_case_set.filepath):
                zip_case_set.file_remove()
            if uncompressed_filepath and os.path.exists(uncompressed_filepath):
                shutil.rmtree(uncompressed_filepath)

            return jsonify(error_code=RET.SERVER_ERR, error_msg=str(e))


class SuiteHandler:
    @staticmethod
    @collect_sql_error
    def create(body):
        _id = Insert(Suite, body.__dict__).insert_id(Suite, "/suite")
        return jsonify(error_code=RET.OK, error_msg="OK", data={"id": _id})


class CaseHandler:
    @staticmethod
    @collect_sql_error
    def create(body):
        _body = body.__dict__

        _suite = Suite.query.filter_by(name=_body.get("suite")).first()
        if not _suite:
            return jsonify(
                error_code=RET.PARMA_ERR,
                error_msg="The suite {} is not exist".format(
                    _body.get("suite")
                )
            )
        _body["suite_id"] = _suite.id
        _body.pop("suite")

        _id = Insert(Case, _body).insert_id(Case, "/case")
        return jsonify(error_code=RET.OK, error_msg="OK", data={"id": _id})


class TemplateCasesHandler:
    @staticmethod
    @collect_sql_error
    def get_all(git_repo_id):
        cases = Case.query.join(Suite).filter(
            Suite.git_repo_id == git_repo_id
        ).all()
        data = [case.to_json() for case in cases]
        return jsonify(
            error_code = RET.OK,
            error_msg="OK",
            data=data,
        )
