/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

export interface TaskEventRecord {
  celery_task_id: null | string;
  created_at: string;
  error_code: null | string;
  host_ip: null | string;
  host_resource_id: null | string;
  id: string;
  level: 'error' | 'info' | 'warning' | string;
  message: string;
  phase: string;
  subject_id: string;
  subject_type: string;
  task_type: string;
}
