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

from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from celeryservice.lib import TaskHandlerBase
from server.model.testcase import CaseNode, Suite
from server.schema.testcase import CreateCaseInstance, SuiteNodeInstance


class CaseNodeCreator(TaskHandlerBase):
    def __init__(self, logger, promise):
        self.promise = promise
        super().__init__(logger)

    def create_suite_node(
            self,
            suite_node_instace: SuiteNodeInstance
    ):
        # 父节点存在性检查
        parent_node = CaseNode.query.filter_by(id=suite_node_instace.parent_id).first()
        if not parent_node or not parent_node.in_set:
            self.logger.error(f"parent node #{suite_node_instace.parent_id} does not exist/not valid")
            return 0

        # 待关联测试套存在性检查
        suite = Suite.query.filter_by(id=suite_node_instace.suite_id).first()
        if not suite:
            self.logger.error(f"suite#{suite_node_instace.suite_id} does not exist, could not be relative")
            return 0

        self.next_period()
        self.promise.update_state(
            state="START",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )

        # 同名suite类型节点存在性检查，如果存在同名节点，则采用已有节点
        same_node = CaseNode.query.filter_by(
            type="suite",
            in_set=True,
            is_root=False,
            title=suite.name,
            permission_type=suite_node_instace.permission_type,
            org_id=suite_node_instace.org_id,
            group_id=suite_node_instace.group_id,
        ).first()
        if same_node:
            return 0
        else:
            testsuite_node = CaseNode(
                permission_type=suite_node_instace.permission_type,
                org_id=suite_node_instace.org_id,
                group_id=suite_node_instace.group_id,
                title=suite.name,
                suite_id=suite.id,
                type="suite",
                in_set=True,
                is_root=False,
            )
            try:
                testsuite_node.add_update()
            except (SQLAlchemyError, IntegrityError) as e:
                self.logger.error(str(e))
                return 0

            parent_node.children.append(testsuite_node)
            parent_node.add_update()

            self.logger.info(f"suite {suite.name} has been added under node {parent_node.title}")
            self.next_period()
            self.promise.update_state(
                state="DONE",
                meta={
                    "start_time": self.start_time,
                    "running_time": self.running_time,
                }
            )
            return testsuite_node.id

    def create_case_node(self, create_case_instance: CreateCaseInstance):
        # 父节点存在性检查
        parent_node = CaseNode.query.filter_by(id=create_case_instance.parent_id).first()
        if not parent_node:
            self.logger.error(f"parent casenode #{create_case_instance.parent_id} is not valid, creating failed.")
            return

        self.next_period()
        self.promise.update_state(
            state="START",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )

        testcase_node = CaseNode(
            permission_type=create_case_instance.permission_type,
            org_id=create_case_instance.org_id,
            group_id=create_case_instance.group_id,
            title=create_case_instance.case_name,
            case_id=create_case_instance.case_id,
            type="case",
            in_set=True,
            is_root=False,
        )
        try:
            testcase_node.add_update()
        except (IntegrityError, SQLAlchemyError) as e:
            self.logger.error(str(e))
            return

        parent_node.children.append(testcase_node)
        parent_node.add_update()

        self.logger.info(f"case {create_case_instance.case_name} has been added under node {parent_node.title}")

        self.next_period()
        self.promise.update_state(
            state="DONE",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )
