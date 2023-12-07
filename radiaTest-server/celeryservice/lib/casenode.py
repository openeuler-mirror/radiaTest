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


class CaseNodeCreator(TaskHandlerBase):
    def __init__(self, logger, promise):
        self.promise = promise
        super().__init__(logger)

    def create_suite_node(
        self,
        parent_id: int, # 被创建suite类型节点的父节点 
        suite_id: int, # 被创建suite类型节点关联的用例ID
        permission_type: str = 'public', # 被创建suite类型节点的权限类型 
        org_id: int = None, # 被创建suite类型节点的所属组织
        group_id: int = None, # 被创建suite类型节点的所属团队
        user_id: str = None, # 创建异步任务的当前用户id
    ):
        # 父节点存在性检查
        parent_node = CaseNode.query.filter_by(id=parent_id).first()
        if not parent_node or not parent_node.in_set:
            self.logger.error(f"parent node #{parent_id} does not exist/not valid")
            return

        # 待关联测试套存在性检查
        suite = Suite.query.filter_by(id=suite_id).first()
        if not suite:
            self.logger.error(f"suite#{suite_id} does not exist, could not be relative")
            return

        self.next_period()
        self.promise.update_state(
            state="START",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )

        testsuite_node = None

        # 同名suite类型节点存在性检查，如果存在同名节点，则采用已有节点
        same_node = CaseNode.query.filter_by(
            type="suite",
            in_set=True,
            is_root=False,
            title=suite.name,
            permission_type=permission_type,
            org_id=org_id,
            group_id=group_id,
        ).first()
        if same_node:
            testsuite_node = same_node
        
        else:
            testsuite_node = CaseNode(
                permission_type=permission_type,
                org_id=org_id,
                group_id=group_id,
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
                return None

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

    def create_case_node(
        self,
        parent_id: int, # 被创建case类型节点的父节点 
        case_name: str, # 被创建case类型节点关联的用例名 
        case_id: int, # 被创建case类型节点关联的用例ID
        permission_type: str = 'public', # 被创建case类型节点的权限类型 
        org_id: int = None, # 被创建case类型节点的所属组织
        group_id: int = None, # 被创建case类型节点的所属团队 
    ):
        # 父节点存在性检查
        parent_node = CaseNode.query.filter_by(id=parent_id).first()
        if not parent_node:
            self.logger.error(f"parent casenode #{parent_id} is not valid, creating failed.")
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
            permission_type=permission_type,
            org_id=org_id,
            group_id=group_id,
            title=case_name,
            case_id=case_id,
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

        self.logger.info(f"case {case_name} has been added under node {parent_node.title}")
        
        self.next_period()
        self.promise.update_state(
            state="DONE",
            meta={
                "start_time": self.start_time,
                "running_time": self.running_time,
            }
        )
