import os
import re
import shutil

from flask import json, jsonify, g, current_app, Response

from server import db, redis_client
from server.utils.redis_util import RedisKey
from server.utils.response_util import RET
from server.utils.db import Edit, Insert, collect_sql_error
from server.model.testcase import Baseline, Suite, Case
from server.schema.testcase import BaselineBaseSchema
from server.utils.files_util import ZipImportFile, ExcelImportFile
from server.utils.sheet import Excel, SheetExtractor 
from server.schema.testcase import BaselineBodyInternalSchema


class CaseImportHandler:
    @staticmethod
    @collect_sql_error
    def loads_data(filetype, filepath, group_id, framework_id):
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
            if not _case:         
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
                            "framework_id": framework_id,
                        }
                    ).single(Suite, '/suite')
                    
                    _suite = Suite.query.filter_by(
                        name=case.get("suite")
                    ).first()

                case["suite_id"] = _suite.id

                suites.add(_suite.id)

                del case["suite"]

                Insert(Case, case).single(Case, "/case")

                _case = Case.query.filter_by(name=case.get("name")).first()

            else:
                del case["suite"]
                case["id"] = _case.id

                Edit(Case, case).single(Case, "/case")

        return suites

    @staticmethod
    @collect_sql_error
    def import_case(file, group_id, framework_id):
        try:
            case_file = ExcelImportFile(file)

            if case_file.filetype:
                case_file.file_save(
                    current_app.config.get("UPLOAD_FILE_SAVE_PATH")
                )

                suites = CaseImportHandler.loads_data(case_file.filetype, case_file.filepath, group_id, framework_id)

                if isinstance(suites, Response):
                    r = json.loads(suites.response[0])
                    raise RuntimeError(r.get("error_msg"))

                case_file.file_remove()

                mesg = "File {} has been import".format(
                    case_file.filename, 
                )

                current_app.logger.info(mesg)

                return jsonify(
                    error_code=RET.OK, 
                    error_msg=mesg, 
                    data=list(suites)
                )

            else:
                mesg = "Filetype of {}.{} is not supported".format(
                    case_file.filename,
                    case_file.filetype,
                )

                current_app.logger.error(mesg)
            
                return jsonify(error_code=RET.OK, error_msg=mesg)
        
        except RuntimeError as e:
            current_app.logger.error(str(e))
            return jsonify(error_code=RET.SERVER_ERR, error_msg=str(e))
        
        finally:
            if os.path.exists(case_file.filepath):
                case_file.file_remove()

    @staticmethod
    @collect_sql_error
    def import_case_with_abspath(filepath, group_id, framework_id):
        try:
            filetype = os.path.splitext(filepath)[-1]

            pattern = r'^([^\.].*)\.(xls|xlsx|csv)$'

            if re.match(pattern, os.path.basename(filepath)) is not None:
                suites = CaseImportHandler.loads_data(
                    filetype[1:], 
                    filepath, 
                    group_id,
                    framework_id
                )

                if isinstance(suites, Response):
                    r = json.loads(suites.response[0])
                    raise RuntimeError(r.get("error_msg"))

                mesg = "File {} has been import".format(
                    os.path.basename(filepath), 
                    filetype,
                )

                current_app.logger.info(mesg)

                return jsonify(
                    error_code=RET.OK, 
                    error_msg=mesg, 
                    data=list(suites)
                )

            else:
                mesg = "File {} is not supported".format(
                    os.path.basename(filepath),
                )

                current_app.logger.error(mesg)
            
                return jsonify(error_code=RET.OK, error_msg=mesg)
        
        except RuntimeError as e:
            current_app.logger.error(str(e))
            return jsonify(error_code=RET.SERVER_ERR, error_msg=str(e))


class BaselineHandler:
    @staticmethod
    @collect_sql_error
    def get(baseline_id, query):
        baseline = Baseline.query.filter_by(id=baseline_id).first()

        current_org_id = int(redis_client.hget(
            RedisKey.user(g.gitee_id), 
            'current_org_id'
        ))

        if current_org_id != baseline.org_id:
            return jsonify(error_code=RET.VERIFY_ERR, error_msg="No right to query")

        if not baseline:
            return jsonify(error_code=RET.NO_DATA_ERR, error_msg="baseline is not exists")
        
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
                raise RuntimeError("baseline should not have parents beyond one")

            source.append(cur.id)
            cur = cur.parent[0]

        return_data["source"] = source

        return jsonify(error_code=RET.OK, error_msg="OK", data=return_data)

    @staticmethod
    @collect_sql_error
    def get_roots(query):
        filter_params = [
            Baseline.is_root.is_(True), 
            Baseline.org_id == redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id'),
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
        _body["org_id"] = redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')

        if not body.parent_id:
            baseline_id = Insert(Baseline, body.__dict__).insert_id()
            return jsonify(error_code=RET.OK, error_msg="OK", data=baseline_id)
        
        parent= Baseline.query.filter_by(id=body.parent_id).first()
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
    def import_case_set(form, file):
        
        def get_this_id(_title, _type, _group_id, _parent_id, _suite_id=None, _case_id=None):
            """已存在节点则直接获取id，不存在的节点新增后获取"""

            _body = BaselineBodyInternalSchema(
                title=_title,
                type=_type,
                group_id=_group_id,
                org_id=redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id'),
                parent_id=_parent_id,
                suite_id=_suite_id,
                case_id=_case_id,
                in_set=True,
            )
            
            filter_params = list()

            if _parent_id is not None:
                parent_baseline = Baseline.query.filter_by(id=_body.parent_id).first()

                if not parent_baseline:
                    raise RuntimeError(
                        "parent id {} is not exist.".format(
                            _body.parent_id
                        )
                    )

                filter_params = [
                    Baseline.title == _body.title,
                    Baseline.type == _type,
                    Baseline.group_id == _body.group_id,
                    Baseline.org_id == _body.group_id,
                    Baseline.suite_id == _body.suite_id,
                    Baseline.case_id == _body.case_id,
                    Baseline.parent.contains(parent_baseline),
                    Baseline.in_set == True
                ]
            else:
                filter_params = [
                    Baseline.title == _body.title,
                    Baseline.type == _type,
                    Baseline.group_id == _body.group_id,
                    Baseline.org_id == _body.group_id,
                    Baseline.suite_id == _body.suite_id,
                    Baseline.case_id == _body.case_id,
                    Baseline.in_set == True
                ]

            baseline = Baseline.query.filter(*filter_params).first()

            if baseline:
                return baseline.id
            else:
                resp = json.loads(BaselineHandler.create(_body).response[0])
                if resp.get("error_code") != RET.OK:
                    raise RuntimeError(resp.get("error_msg"))

                return resp["data"]

        def deep_create(_filepath, _parent_id, _group_id, _framework_id, _org_id):
            _title = ""
            if not _parent_id:
                _title = "用例集"
            else:
                _title =  os.path.basename(_filepath)

            _name = os.path.basename(_filepath).split('.')[0]
            _ext = os.path.basename(_filepath).split('.')[-1]

            if os.path.isfile(_filepath) and _ext in ['xlsx', 'xls', 'csv']:
                _body = BaselineBodyInternalSchema(
                    title=_name,
                    type="directory",
                    group_id=_group_id,
                    org_id=_org_id,
                    parent_id=_parent_id,
                    in_set=True,
                )
                resp = json.loads(BaselineHandler.create(_body).response[0])
                if resp.get("error_code") != RET.OK:
                    current_app.logger.error(resp.get("error_msg"))
                    return
  
                _file_id = resp["data"]

                _resp = json.loads(
                    CaseImportHandler.import_case_with_abspath(
                        _filepath,
                        _group_id, 
                        _framework_id
                    ).response[0]
                )
                if not _resp.get("data"):
                    return

                _suites = _resp["data"]

                for _suite_id in _suites:
                    _suite = Suite.query.filter_by(id=_suite_id).first()

                    if not _suite:
                        continue
                    
                    _this_suite_id = get_this_id(
                        _title=_suite.name,
                        _type="suite",
                        _group_id=_group_id,
                        _suite_id=_suite.id,
                        _parent_id=_file_id,
                    )

                    for case in _suite.case:
                        _this_id = get_this_id(
                            _title=case.name,
                            _type="case",
                            _group_id=_group_id,
                            _parent_id=_this_suite_id,
                            _case_id=case.id,
                        )
                return
            
            if not os.path.isdir(_filepath):
                return
            
            _this_id = get_this_id(
                _title=_title,
                _type="directory",
                _group_id=_group_id,
                _parent_id=_parent_id,
            )

            subfiles = os.listdir(_filepath)

            for subfile in subfiles:
                deep_create(
                    _filepath="{}/{}".format(_filepath, subfile), 
                    _parent_id=_this_id, 
                    _group_id=_group_id,
                    _org_id=redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
                )

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

                deep_create(
                    _filepath=uncompressed_filepath,
                    _parent_id=None,
                    _group_id=form.get("group_id"),
                    _framework_id=form.get("framework_id"),
                    _org_id=redis_client.hget(RedisKey.user(g.gitee_id), 'current_org_id')
                )
                
                return jsonify(error_code=RET.OK, error_msg="OK")
            
            else:
                return jsonify(error_code=RET.FILE_ERR, error_msg="filetype is not supported")
        
        except RuntimeError as e:
            current_app.logger.error(str(e))
            return jsonify(error_code=RET.SERVER_ERR, error_msg=str(e))

        finally:
            if os.path.exists(zip_case_set.filepath):
                zip_case_set.file_remove()
                if os.path.exists(uncompressed_filepath):
                    shutil.rmtree(uncompressed_filepath)


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
                error_mesg="The suite {} is not exist".format(
                    _body.get("suite")
                )
            )
        _body["suite_id"] = _suite.id
        _body.pop("suite")

        _id = Insert(Case, _body).insert_id(Case, "/case") 
        return jsonify(error_code=RET.OK, error_msg="OK", data={"id": _id})

