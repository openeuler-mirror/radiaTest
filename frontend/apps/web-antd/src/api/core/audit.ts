import type { PageParams, PaginatedResponse } from './pagination';

import { requestClient } from '#/api/request';

export interface AuditLogListParams extends PageParams {
  action?: string;
  actor_username?: string;
  ended_at?: string;
  started_at?: string;
  target_type?: string;
}

export interface AuditLogRecord {
  action: string;
  actor_user_id: null | string;
  actor_username: null | string;
  created_at: string;
  detail: Record<string, unknown>;
  id: string;
  target_id: null | string;
  target_type: string;
}

export async function getAuditLogsApi(params: AuditLogListParams) {
  return requestClient.get<PaginatedResponse<AuditLogRecord>>('/audit-logs', {
    params,
  });
}
