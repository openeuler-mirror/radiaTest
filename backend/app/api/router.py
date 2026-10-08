# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from fastapi import APIRouter

from app.api.v1 import health
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.feishu.router import router as feishu_router
from app.modules.leases.router import lease_events_router, leases_router
from app.modules.leases.router import resources_router as lease_resources_router
from app.modules.notifications.router import router as notifications_router
from app.modules.pipelines.router import router as pipelines_router
from app.modules.rc_management.router import (
    compares_router as rc_compares_router,
)
from app.modules.rc_management.router import (
    milestones_router as rc_milestones_router,
)
from app.modules.rc_management.router import (
    versions_router as rc_versions_router,
)
from app.modules.resources.router import router as resources_router
from app.modules.test_management.router import cases_router as test_cases_router
from app.modules.test_management.router import jobs_router as test_jobs_router
from app.modules.test_management.router import templates_router as test_job_templates_router
from app.modules.tickets.router import router as tickets_router
from app.modules.users.router import router as users_router
from app.modules.vms.router import (
    images_router as vm_images_router,
)
from app.modules.vms.router import isos_router as vm_isos_router
from app.modules.vms.router import (
    requests_router as vm_requests_router,
)
from app.modules.vms.router import (
    vms_router,
)

api_router = APIRouter()
# 聚合所有业务路由到单一 api_router，由 install_api_runtime 统一挂载到 /api/v1。
# 新增模块在此 include，不创建并行入口。
api_router.include_router(health.router)
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(users_router)
api_router.include_router(notifications_router)
api_router.include_router(feishu_router)
api_router.include_router(resources_router)
api_router.include_router(rc_versions_router)
api_router.include_router(rc_milestones_router)
api_router.include_router(rc_compares_router)
api_router.include_router(test_cases_router)
api_router.include_router(test_jobs_router)
api_router.include_router(test_job_templates_router)
api_router.include_router(tickets_router)
api_router.include_router(vm_images_router)
api_router.include_router(vm_isos_router)
api_router.include_router(vm_requests_router)
api_router.include_router(vms_router)
api_router.include_router(lease_resources_router)
api_router.include_router(leases_router)
api_router.include_router(lease_events_router)
api_router.include_router(pipelines_router)
