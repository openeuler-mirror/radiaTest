import type { PageParams, PaginatedResponse } from './pagination';

import { requestClient } from '#/api/request';

export interface LeaseEventListParams extends PageParams {
  actor_username?: string;
  ended_at?: string;
  event_type?: string;
  primary_ip?: string;
  resource_code?: string;
  resource_type?: string;
  started_at?: string;
}

export interface LeaseEventRecord {
  actor_user_id: null | string;
  actor_username: null | string;
  created_at: string;
  detail: Record<string, unknown>;
  event_type: string;
  id: string;
  lease_id: string;
  primary_ip: null | string;
  resource_code: null | string;
  resource_id: string;
  resource_type: null | string;
}

export async function getLeaseEventsApi(params: LeaseEventListParams) {
  return requestClient.get<PaginatedResponse<LeaseEventRecord>>(
    '/lease-events',
    { params },
  );
}
