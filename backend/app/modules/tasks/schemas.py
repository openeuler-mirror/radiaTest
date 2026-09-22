# Copyright (c) [2026] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TaskEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_type: str
    subject_type: str
    subject_id: str
    celery_task_id: str | None
    level: str
    phase: str
    message: str
    host_resource_id: str | None
    host_ip: str | None
    error_code: str | None
    created_at: datetime
