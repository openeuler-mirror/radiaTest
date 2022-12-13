import os
from datetime import timedelta, datetime

import pytz
from flask import jsonify, g, current_app, send_file
import sqlalchemy
from werkzeug.utils import secure_filename
from pypinyin import lazy_pinyin

from server import redis_client
from server.model.task import Task, TaskMilestone
from server.model.organization import Organization
from server.model.group import Group, ReUserGroup
from server.model.user import User
from server.model.milestone import Milestone
from server.model.requirement import (
    Requirement,
    RequirementAcceptor, 
    RequirementProgress, 
    RequirementPackage,
    RequirementPublisher
)
from server.utils.page_util import PageUtil
from server.utils.response_util import RET
from server.utils.file_util import ImportFile
from server.utils.db import Insert, Delete, collect_sql_error
from server.utils.redis_util import RedisKey
from server.apps.task.handlers import HandlerTask
from server.schema.task import AddTaskSchema


class REQ_STATUS:
    IDLE = 'idle'
    ACCEPTED = 'accepted'
    VALIDATED = 'validated'


class RequirementCreator:
    def __init__(self, body: dict):
        self._packages = body.pop("packages")
        self._milestone_id_list = body.pop("milestones")

        self.body = body
        self.body.update({
            "status": REQ_STATUS.IDLE,
            "org_id": redis_client.hget(
                RedisKey.user(g.gitee_id), 
                "current_org_id"
            ),
        })
        
        self._milestones = []
        for _milstone_id in self._milestone_id_list:
            _milestone = Milestone.query.filter_by(id=_milstone_id).first()
            if not _milestone:
                raise RuntimeError(f"milestone {_milstone_id} dose not exist, requirement create failed")
            self._milestones.append(_milestone)

    def create_requirement(self):
        return Insert(Requirement, self.body).insert_id(Requirement, '/requirement')

    def relate_milestones(self, _requirement_id: int):
        _requirement = Requirement.query.filter_by(id=_requirement_id).first()
        for _milestone in self._milestones:
            _requirement.milestones.append(_milestone)
            _requirement.add_update(Requirement, "/requirement")

    def create_packages(self, _requirement_id: int):
        _validator_id = g.gitee_id if self.body.get("publisher_type") == "person" else sqlalchemy.null()

        for _package in self._packages:
            _ = Insert(
                RequirementPackage,
                {
                    "name": _package.get("name"),
                    "targets": ",".join(_package.get("targets")),
                    "requirement_id": _requirement_id,
                    "validator_id": _validator_id,
                }
            ).insert_id()


class RequirementHandler:
    @staticmethod
    def get_all(query):
        filter_params = [
            Requirement.org_id == redis_client.hget(
                RedisKey.user(g.gitee_id), 
                "current_org_id"
            ),
        ]
        if query.status:
            filter_params.append(Requirement.status == query.status)
        if query.title:
            filter_params.append(Requirement.title.like(f"%{query.title}%"))
        if query.payload and query.payload_operator:
            if query.payload_operator == "=":
                filter_params.append(Requirement.payload == float(query.payload))
            elif query.payload_operator == ">":
                filter_params.append(Requirement.payload > float(query.payload))
            elif query.payload_operator == ">=":
                filter_params.append(Requirement.payload >= float(query.payload))
            elif query.payload_operator == "<":
                filter_params.append(Requirement.payload < float(query.payload))
            elif query.payload_operator == "<=":
                filter_params.append(Requirement.payload <= float(query.payload))
        if query.period and query.period_operator:
            if query.period_operator == "=":
                filter_params.append(Requirement.period == int(query.period))
            elif query.period_operator == ">":
                filter_params.append(Requirement.period > int(query.period))
            elif query.period_operator == ">=":
                filter_params.append(Requirement.period >= int(query.period))
            elif query.period_operator == "<":
                filter_params.append(Requirement.period < int(query.period))
            elif query.period_operator == "<=":
                filter_params.append(Requirement.period <= int(query.period))
        if query.influence_require:
            filter_params.append(
                Requirement.influence_require <= int(query.influence_require)
            )
        if query.behavior_require:
            filter_params.append(
                Requirement.influence_require <= int(query.behavior_require)
            )
        if query.total_reward:
            filter_params.append(Requirement.total_reward >= query.total_reward)
        
        query_filter = Requirement.query.filter(
            *filter_params
        ).order_by(
            Requirement.create_time.desc()
        )

        def page_func(item):
            requirement_dict = item.to_json()
            return requirement_dict

        page_dict, e = PageUtil.get_page_dict(
            query_filter, 
            query.page_num, 
            query.page_size, 
            func=page_func
        )
        if e:
            return jsonify(error_code=RET.SERVER_ERR, error_msg=f'get requirement page error {e}')
        return jsonify(error_code=RET.OK, error_msg="OK", data=page_dict)

    @staticmethod
    @collect_sql_error
    def free_publish(org_id: int, body: dict):
        _org = Organization.query.filter_by(
            id=int(redis_client.hget(RedisKey.user(g.gitee_id), "current_org_id"))
        ).first()
        if not _org or _org.id != org_id:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg="Unauthoried Access",
            )

        creator = RequirementCreator(body)
        _requirement_id = creator.create_requirement()

        publisher_body = {
            "type": "organization",
            "requirement_id": _requirement_id, 
            "user_id": g.gitee_id,
            "org_id": _org.id,
        }
        _ = Insert(RequirementPublisher, publisher_body).insert_id()

        creator.relate_milestones(_requirement_id)
        creator.create_packages(_requirement_id)

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )
    
    @staticmethod
    @collect_sql_error
    def publish(body: dict):
        _publisher_type = body.pop("publisher_type")
        _publisher_group_id = body.pop("publisher_group_id")

        creator = RequirementCreator(body)

        _publisher = None
        if _publisher_type == "group":
            group = Group.query.filter_by(id=_publisher_group_id).first()
            if not group:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"the group publisher {_publisher_group_id} is not valid"
                )
            _publisher = group
            _foreign_key = {
                "user_id": g.gitee_id,
                "group_id": group.id
            }
        elif _publisher_type == "person":
            user = User.query.filter_by(gitee_id=g.gitee_id).first()
            if not user:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"the person publisher {g.gitee_id} is not valid"
                )
            _publisher = user
            _foreign_key = {"user_id": user.gitee_id}
        if not _publisher:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the publisher does not exist"
            )
        
        if _publisher.influence < body.get("total_reward"):
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="could not publish the requirement with reward higher than the influence owned by publisher"
            )
        
        _requirement_id = creator.create_requirement()

        _publisher_body = {
            "type": _publisher_type,
            "requirement_id": _requirement_id,   
        }
        _publisher_body.update(_foreign_key)
        _ = Insert(RequirementPublisher, _publisher_body).insert_id()

        creator.relate_milestones(_requirement_id)
        creator.create_packages(_requirement_id)

        _publisher.influence -= body.get("total_reward")
        _publisher.add_update_influence(User, '/rank')

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )


def in_group(user_id, group_id):
    re_user_group = ReUserGroup.query.filter_by(
        user_gitee_id=user_id, 
        group_id=group_id,
        is_delete=False,
    ).first()
    if not re_user_group:
        return False
    return True


class RequirementItemHandler:
    def __init__(self, requirement_id: int, body: dict = None):
        self.requirement = Requirement.query.filter_by(id=requirement_id).first()
        if not self.requirement:
            raise RuntimeError("the requirement does not exist")

        self.body = body
        self.statement_attachment_path = self._get_attachment_dir("statement")
        self.progress_attachment_path = self._get_attachment_dir("progress")
        self.validation_attachment_path = self._get_attachment_dir("validation")

    def _get_attachment_dir(self, _type: str):
        _title = self.requirement.create_time.strftime("%Y-%m-%d-%H-%M-%S")

        path = os.path.join(
            current_app.config.get("REQUIREMENT_ATTACHMENT_PATH"),
            f"{self.requirement.title}_{_title}",
            _type,
        )

        if not os.path.isdir(path):
            os.makedirs(path)

        return path

    def _handle_accepted(self, action):
        if self.requirement.status == REQ_STATUS.ACCEPTED and self.requirement.acceptor:
            raise RuntimeError(
                f"the requirement has already been accepted, could not be {action}"
            )
    
    def _handle_not_accepted(self, msg):
        if self.requirement.status != REQ_STATUS.ACCEPTED:
            raise RuntimeError(
                f"could not {msg} a requirement not in accepted status"
            )

    def _handle_not_validated(self, msg):
        if self.requirement.status != REQ_STATUS.VALIDATED:
            raise RuntimeError(
                f"could not {msg} a requirement not in validated status"
            )

    def _handle_publisher_acceptor_accord(self):
        _accord = False
        if self.requirement.publisher[0].type == "person":
            _accord = (
                self.body.get("acceptor_type") == "person" 
                and self.requirement.publisher[0].user_id == g.gitee_id
            ) or (
                self.body.get("acceptor_type") == "group" 
                and in_group(
                    self.requirement.publisher[0].user_id,
                    self.body.get("acceptor_group_id")
                )
            )
        elif self.requirement.publisher[0].type == "group":
            _accord = (
                self.body.get("acceptor_type") == "person" 
                and in_group(
                    g.gitee_id,
                    self.requirement.publisher[0].group_id
                )
            ) or (
                self.body.get("acceptor_type") == "group" 
                and self.requirement.publisher[0].group_id == self.body.get("acceptor_group_id")
            )

        if _accord:
            raise RuntimeError("the publisher could not be the same with acceptor")

    def _handle_not_acceptor(self, msg):
        if self.requirement.acceptor[0].user_id != g.gitee_id:
            raise RuntimeError(f"only the acceptor could {msg} the requirement")

    def _handle_not_group_acceptor(self, msg):
        if self.requirement.acceptor[0].type != "group":
            raise RuntimeError(f"only group acceptor could {msg} the requirement")

    def _handle_not_publisher(self, msg):
        if self.requirement.publisher[0].user_id != g.gitee_id:
            raise RuntimeError(f"only the publisher could {msg} the requirement")

    def _handle_not_in_project(self, msg):
        if (
            (
                self.requirement.acceptor
                and g.gitee_id != self.requirement.acceptor[0].user_id
            )
            and (
                g.gitee_id != self.requirement.publisher[0].user_id
            )
            and (
                self.requirement.acceptor
                and self.requirement.acceptor[0].type == "group" 
                and in_group(
                    g.gitee_id, 
                    self.requirement.acceptor[0].group_id
                )
            )
            and (
                self.requirement.publisher[0].type == "group"
                and in_group(
                    g.gitee_id,
                    self.requirement.publisher[0].group_id
                )
            )
        ):
            raise RuntimeError(
                "only the member involved in this project "\
                f"could {msg}"
            )
        
    def get_info(self):
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=self.requirement.to_json()
        )

    @collect_sql_error
    def delete(self):
        self._handle_accepted('deleted')
        self._handle_not_publisher('delete')
        
        Delete(
            Requirement, 
            {"id": self.requirement.id}
        ).single(Requirement, "/requirement")

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )

    @collect_sql_error
    def accept(self):
        self._handle_accepted('accepted')
        self._handle_publisher_acceptor_accord()
        
        if self.body.get("acceptor_type") == "group":
            _group = Group.query.filter_by(id=self.body.get("acceptor_group_id")).first()
            if _group.org_id != int(redis_client.hget(RedisKey.user(g.gitee_id), "current_org_id")):
                raise RuntimeError(
                    f"the group {_group.name} does not belong to current organization"
                )
            if _group.influence < self.requirement.influence_require:
                raise RuntimeError(
                    f"the group {_group.name} does not satisfy the influence requirement"
                )
            if _group.behavior < self.requirement.behavior_require:
                raise RuntimeError(
                    f"the group {_group.name} does not satisfy the behavior requirement"
                )
        else:
            _user = User.query.filter_by(gitee_id=int(g.gitee_id)).first()
            if _user.influence < self.requirement.influence_require:
                raise RuntimeError(
                    f"not satisfy the influence requirement"
                )
            if _user.behavior < self.requirement.behavior_require:
                raise RuntimeError(
                    f"not satisfy the behavior requirement"
                )

        _acceptor_body = {
            "type": self.body.get("acceptor_type"),
            "user_id": g.gitee_id,
            "requirement_id": self.requirement.id,
        }
        if self.body.get("acceptor_type") == "group":
            _acceptor_id = self.body.get("acceptor_group_id")
            _acceptor_body.update({
                "group_id": _acceptor_id,
            })
        else:
            _acceptor_id = g.gitee_id

        _ = Insert(RequirementAcceptor, _acceptor_body).insert_id()

        _now = datetime.now(tz=pytz.timezone("Asia/Shanghai"))
        _now_str = _now.strftime('%Y%m%d')
        task_title = f"{self.requirement.title}_{_now_str}"
        deadline = (_now + timedelta(days=self.requirement.period)).strftime('%Y%m%d')
        addtaskschema = AddTaskSchema(
            title=task_title,
            creator_id=int(g.gitee_id),
            type=self.body.get("acceptor_type").upper(),
            start_time=_now_str,
            abstract=self.requirement.remark,
            content=self.requirement.description,
            executor_id=int(g.gitee_id),
            executor_type=self.body.get("acceptor_type").upper(),
            deadline=deadline,
            status_id=1,
            group_id=self.body.get("acceptor_group_id"),
            org_id=int(redis_client.hget(RedisKey.user(g.gitee_id), "current_org_id")),
            is_manage_task=True,
            automatic_finish=True,
        )
        HandlerTask.create(addtaskschema)
        
        _task = Task.query.filter_by(title=task_title).first()
        for _milestone in self.requirement.milestones:
            _task.milestones.append(
                TaskMilestone(task_id=_task.id, milestone_id=_milestone.id)
            )

        self.requirement.status = REQ_STATUS.ACCEPTED
        self.requirement.task_id = _task.id
        self.requirement.add_update(Requirement, '/requirement')

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )

    @collect_sql_error
    def reject(self):
        self._handle_not_accepted('reject')
        self._handle_not_acceptor('reject')
        
        _acceptor = self.requirement.acceptor[0]
        acceptor = RequirementAcceptor.query.filter_by(id=_acceptor.id).first()
        if acceptor:
            acceptor.delete()

        for _package in self.requirement.packages:
            _package.task_id = sqlalchemy.null()
            _package.completions = sqlalchemy.null()
            _package.validator_id = sqlalchemy.null()
            _package.add_update()

        for _progress in self.requirement.progresses:
            _progress.delete()
        
        self.requirement.status = REQ_STATUS.IDLE
        self.requirement.task_id = sqlalchemy.null()
        self.requirement.add_update(Requirement, '/requirement')

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )
    
    @collect_sql_error
    def validate(self):
        self._handle_not_accepted('validate')
        self._handle_not_publisher('validate')
        
        if self.requirement.acceptor[0].type == "person":
            acceptor = User.query.filter_by(gitee_id=self.requirement.acceptor[0].user_id).first()
            acceptor.influence += self.requirement.total_reward
        elif self.requirement.acceptor[0].type == "group":
            self.requirement.dividable_reward = self.requirement.total_reward
            acceptor = Group.query.filter_by(id=self.requirement.acceptor[0].group_id).first()
            acceptor.influence += self.requirement.total_reward
        acceptor.add_update_influence(User, '/rank')
        
        self.requirement.statement_locked = True
        self.requirement.progress_locked = True
        self.requirement.validation_locked = True
        self.requirement.status = REQ_STATUS.VALIDATED
        self.requirement.add_update(Requirement, '/requirement')
        
        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )
    
    @collect_sql_error
    def upload_attachment(self, _type, file):
        if getattr(self.requirement, f"{_type}_locked"):
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="these attachments are locked, could not be changed",
            )

        self._handle_not_in_project("upload the attachment")
        _file = ImportFile(file)

        if _type == "statement":
            self._handle_not_publisher('upload statement attachment')
            try:
                _file.file_save(self.statement_attachment_path, timestamp=False)
            except RuntimeError as e:
                return jsonify(
                    error_code=RET.DATA_EXIST_ERR,
                    error_msg=str(e)
                )
            if not self.requirement.statement_filelist:
                self.requirement.statement_filelist = f"{_file.filename}.{_file.filetype}"
            else:
                self.requirement.statement_filelist += f',{_file.filename}.{_file.filetype}'
            self.requirement.add_update()

            return jsonify(
                error_code=RET.OK,
                error_msg="OK"
            )

        elif _type == "progress":
            try:
                _file.file_save(self.progress_attachment_path, timestamp=False)
            except RuntimeError as e:
                return jsonify(
                    error_code=RET.DATA_EXIST_ERR,
                    error_msg=str(e)
                )
            if not self.requirement.progress_filelist:
                self.requirement.progress_filelist = f"{_file.filename}.{_file.filetype}"
            else:
                self.requirement.progress_filelist += f',{_file.filename}.{_file.filetype}'
            self.requirement.add_update()

            return jsonify(
                error_code=RET.OK,
                error_msg="OK"
            )
            
        else:
            try:
                _file.file_save(self.validation_attachment_path, timestamp=False)
            except RuntimeError as e:
                return jsonify(
                    error_code=RET.DATA_EXIST_ERR,
                    error_msg=str(e)
                )
            if not self.requirement.validation_filelist:
                self.requirement.validation_filelist = f"{_file.filename}.{_file.filetype}"
            else:
                self.requirement.validation_filelist += f',{_file.filename}.{_file.filetype}'
            self.requirement.add_update()

            return jsonify(
                error_code=RET.OK,
                error_msg="OK"
            )

    def _get_attachment_filepath(self, _type, filename):
        self._handle_not_in_project("download the attachment")
        if _type == "statement":
            filepath = f"{self.statement_attachment_path}/{secure_filename(''.join(lazy_pinyin(filename)))}"

        elif _type == "progress":
            filepath = f"{self.progress_attachment_path}/{secure_filename(''.join(lazy_pinyin(filename)))}"

        elif _type == "validation":
            self._handle_not_publisher('download validation attachment')
            filepath = f"{self.validation_attachment_path}/{secure_filename(''.join(lazy_pinyin(filename)))}"

        if not os.path.isfile(filepath):
            raise RuntimeError("the file does not exist")

        return filepath

    def get_filelist(self, _type: str):
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data = self.requirement.get_filelist(_type)
        ) 

    def download_attachment(self, _type: str, filename: str):
        filepath = self._get_attachment_filepath(_type, filename)

        return send_file(filepath, as_attachment=True)

    def lock_attachment(self, _type: str, locked: bool):
        self._handle_not_publisher(f'lock {_type} attachment')
        if self.requirement.status == REQ_STATUS.VALIDATED:
            raise RuntimeError(
                f"could not change lock status while the requirement was validated"
            )

        setattr(self.requirement, f"{_type}_locked", locked)
        self.requirement.add_update()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )

    @collect_sql_error
    def delete_attachment(self, _type, filename):
        if getattr(self.requirement, f"{_type}_locked"):
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="these attachments are locked, could not be changed",
            )

        _filelist = []
        if _type == "statement":
            self._handle_not_publisher("delete statement attachment")
            _filelist = self.requirement.statement_filelist.split(',')
        elif _type == "progress":
            _filelist = self.requirement.progress_filelist.split(',')
        elif _type == "validation":
            _filelist = self.requirement.validation_filelist.split(',')
        
        if filename not in _filelist:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg=f"{_type} attachment {filename} not exist"
            )

        filepath = self._get_attachment_filepath(_type, filename)
        os.remove(filepath)

        _filelist.pop(_filelist.index(filename))
        _value = ','.join(_filelist) if len(_filelist) > 0 else sqlalchemy.null()
        setattr(self.requirement, f"{_type}_filelist", _value)
        self.requirement.add_update()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )


    def get_progress(self):
        progresses = RequirementProgress.query.filter_by(
            requirement_id=self.requirement.id
        ).order_by(
            RequirementProgress.create_time.desc()
        ).all()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=[progress.to_json() for progress in progresses]
        )

    def feedback_progress(self, body: dict):
        self._handle_not_accepted('feedback progress')
        self._handle_not_in_project("feedback progress")
        body.update({
            "requirement_id": self.requirement.id
        })
        return Insert(RequirementProgress, body).single()

    def edit_progress(self, progress_id: int, body: dict):
        self._handle_not_accepted('feedback progress')
        self._handle_not_in_project("edit progress")
        progress = RequirementProgress.query.filter_by(id=progress_id).first()
        if not progress:
            return jsonify(
                error_code=RET.OK,
                error_msg="the progress does not exist"
            )
        progress.type = body.get("type")
        progress.percentage = body.get("percentage")
        progress.content = body.get("content")
        progress.add_update()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )

    def delete_progress(self, progress_id: int):
        self._handle_not_accepted('feedback progress')
        self._handle_not_in_project("delete progress")
        progress = RequirementProgress.query.filter_by(id=progress_id).first()
        if not progress:
            return jsonify(
                error_code=RET.OK,
                error_msg="the progress does not exist"
            )
        progress.delete()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )

    def get_attributors(self):
        self._handle_not_validated('confirm attributors')
        if self.requirement.acceptor[0].type != 'group':
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="this requirement is accepted by individual acceptor"
            )
        _attributors = set([self.requirement.acceptor[0].user_id])
        for _package in self.requirement.packages:
            if not _package.task:
                continue
            _attributors.add(_package.task.executor_id)
            for _participant in _package.task.participants:
                _attributors.add(_participant.participant_id)
        
        attributors = [
            User.query.filter_by(gitee_id=_attributor_id).first() for _attributor_id in _attributors
        ]
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=[attributor.to_summary() for attributor in attributors],
        )

    def divide_reward(self, strategies: list):
        self._handle_not_validated('divide rewards for')
        self._handle_not_acceptor('divide rewards for')
        self._handle_not_group_acceptor('divide rewards for')
        _sum = 0
        user_dict = {}
        for strategy in strategies:
            _sum += int(strategy.reward)
            user = User.query.filter_by(gitee_id=int(strategy.user_id)).first()
            if not user:
                return jsonify(
                    error_code=RET.NO_DATA_ERR,
                    error_msg=f"user {strategy.user_id} does not exist. dividing failed"
                )
            user_dict[strategy.user_id] = user

        if _sum > self.requirement.dividable_reward:
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="there are no enough dividable rewards"
            )
        
        _sum = 0
        for strategy in strategies:
            user = user_dict.get(strategy.user_id)
            if not in_group(user.gitee_id, self.requirement.acceptor[0].group_id):
                continue

            user.influence += strategy.reward
            _sum += strategy.reward
            user.add_update_influence(User, '/rank')

        self.requirement.dividable_reward -= _sum
        self.requirement.add_update(Requirement, '/requirement')

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=self.requirement.dividable_reward,
        )

    def get_packages(self):
        _packages = self.requirement.packages
        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
            data=[_package.to_json() for _package in _packages]
        )


class RequirementPackageHandler:
    def __init__(self, requirement_id, package_id):
        self.requirement = Requirement.query.filter_by(id=requirement_id).first()
        if not self.requirement:
            raise RuntimeError("the requirement does not exist")
        self.package = RequirementPackage.query.filter_by(id=package_id).first()
        if not self.package:
            raise RuntimeError("the package does not exist")
    
    def _handle_wrong_status(self, status):
        if self.requirement.status != status:
            raise RuntimeError(f"the task should be {status}")

    def _handle_person_publisher(self):
        if self.requirement.publisher[0].type == "person":
            raise RuntimeError("the publisher type should not be person")

    def _handle_person_acceptor(self):
        if self.requirement.acceptor[0].type == "person":
            raise RuntimeError("the acceptor type should not be person")

    def _get_user(self, user_id):
        user = User.query.filter_by(gitee_id=user_id).first()
        if not user:
            raise RuntimeError("the user does not exist")
        return user

    def set_validator(self, user_id):
        self._handle_wrong_status(REQ_STATUS.ACCEPTED)
        self._handle_person_publisher()
        user = self._get_user(user_id)

        if (
            self.requirement.publisher[0].type == "group" 
            and not in_group(user.gitee_id, self.requirement.publisher[0].group_id)
        ):
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="could only set validator who is in the publisher group"
            )
        elif self.requirement.publisher[0].org_id != int(
            redis_client.hget(
                RedisKey.user(g.gitee_id), 
                "current_org_id"
            )
        ):
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg="could only set validator who is in the publisher organization"
            )
        
        self.package.validator_id = user.gitee_id
        self.package.add_update()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )

    def validate(self, completions: list):
        if self.package.validator_id != g.gitee_id:
            return jsonify(
                error_code=RET.UNAUTHORIZE_ERR,
                error_msg="only the validator could validate requirement package"
            ) 

        for item in completions:
            if item not in self.package.targets:
                return jsonify(
                    error_code=RET.BAD_REQ_ERR,
                    error_msg=f"the completions item {item} not in targets"
                )

        _completions = ','.join(completions)
        self.package.completions = _completions
        self.package.add_update()
        return jsonify(
            error_code=RET.OK,
            error_msg="OK"
        )
    
    def create_relative_task(self, body: dict):
        self._handle_wrong_status(REQ_STATUS.ACCEPTED)
        self._handle_person_acceptor()

        if self.package.task_id:
            return jsonify(
                error_code=RET.DATA_EXIST_ERR,
                error_msg='the relative task of this package has been exist',
            )

        _user = self._get_user(body.get("executor_id"))
        _group_id = self.requirement.acceptor[0].group_id
        if not in_group(_user.gitee_id, _group_id):
            return jsonify(
                error_code=RET.BAD_REQ_ERR,
                error_msg=f"the user {_user.gitee_name} is not in acceptor group"
            )

        _parent = Task.query.filter_by(id=self.requirement.task_id).first()
        if not _parent:
            return jsonify(
                error_code=RET.NO_DATA_ERR,
                error_msg="the root task relatived to this requirement does not exist, "\
                    "then the subtask could not be created. "
            )

        _now = datetime.now(tz=pytz.timezone("Asia/Shanghai"))

        task_body = {
            "permission_type": _parent.permission_type,
            "title": f"{self.package.name}_{self.requirement.title}_"\
                f"{datetime.now(tz=pytz.timezone('Asia/Shanghai')).strftime('%Y%m%d%H%M%S')}",
            "type": _parent.type,
            "creator_id": int(g.gitee_id),
            "start_time": _now,
            "executor_id": _user.gitee_id,
            "deadline": _parent.deadline,
            "status_id": 1,
            "group_id": _parent.group_id,
            "org_id": _parent.org_id,
            "is_manage_task": True,
            "automatic_finish": True,
        }
        _child_id = Insert(Task, task_body).insert_id()
        child = Task.query.filter_by(id=_child_id).first()

        child.parents.append(_parent)
        for milestone in _parent.milestones:
            child.milestones.append(
                TaskMilestone(
                    task_id=child.id,
                    milestone_id=milestone.milestone_id,
                )
            )

        child.add_update()
        
        self.package.task_id = _child_id
        self.package.add_update()

        return jsonify(
            error_code=RET.OK,
            error_msg="OK",
        )