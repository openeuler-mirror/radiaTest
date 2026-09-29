import type { PageParams, PaginatedResponse } from './pagination';

import { requestClient } from '#/api/request';

export type TicketMatchMode = 'and' | 'or';
export type TicketPriority = 'HIGH' | 'LOW' | 'MEDIUM';
export type TicketStatus = 'ACCEPTED' | 'COMPLETED' | 'PENDING' | 'REJECTED';
export type TicketType = 'BUG' | 'REQ';

export interface TicketCommentRecord {
  author_display_name: null | string;
  author_user_id: string;
  author_username: string;
  body: string;
  created_at: string;
  id: string;
}

export interface TicketRecord {
  assignee_display_name: null | string;
  assignee_user_id: null | string;
  assignee_username: null | string;
  body: string;
  completed_at: null | string;
  created_at: string;
  id: number;
  is_overdue: boolean;
  planned_completion_at: null | string;
  priority: null | TicketPriority;
  rejection_reason: null | string;
  status: TicketStatus;
  submitter_display_name: null | string;
  submitter_user_id: string;
  submitter_username: string;
  ticket_type: TicketType;
  title: string;
  updated_at: string;
}

export interface TicketDetailRecord extends TicketRecord {
  comments: TicketCommentRecord[];
}

export interface TicketListParams extends PageParams {
  assignee?: string;
  match?: TicketMatchMode;
  priority?: 'UNSET' | TicketPriority;
  status?: TicketStatus;
  submitter?: string;
  ticket_id?: number;
  ticket_type?: TicketType;
  title?: string;
}

export interface TicketCreatePayload {
  body: string;
  ticket_type: TicketType;
  title: string;
}

export interface TicketContentUpdatePayload {
  body?: string;
  title?: string;
}

export interface TicketHandlingPayload {
  assignee_user_id: string;
  planned_completion_at: string;
  priority: TicketPriority;
}

export async function getTicketsApi(params: TicketListParams) {
  return requestClient.get<PaginatedResponse<TicketRecord>>('/tickets', {
    params,
  });
}

export async function createTicketApi(payload: TicketCreatePayload) {
  return requestClient.post<TicketDetailRecord>('/tickets', payload);
}

export async function getTicketApi(ticketId: number) {
  return requestClient.get<TicketDetailRecord>(`/tickets/${ticketId}`);
}

export async function updateTicketApi(
  ticketId: number,
  payload: TicketContentUpdatePayload,
) {
  return requestClient.request<TicketDetailRecord>(`/tickets/${ticketId}`, {
    data: payload,
    method: 'PATCH',
  });
}

export async function acceptTicketApi(
  ticketId: number,
  payload: TicketHandlingPayload,
) {
  return requestClient.post<TicketDetailRecord>(
    `/tickets/${ticketId}/accept`,
    payload,
  );
}

export async function rejectTicketApi(ticketId: number, reason: string) {
  return requestClient.post<TicketDetailRecord>(`/tickets/${ticketId}/reject`, {
    reason,
  });
}

export async function updateTicketHandlingApi(
  ticketId: number,
  payload: Partial<TicketHandlingPayload>,
) {
  return requestClient.request<TicketDetailRecord>(
    `/tickets/${ticketId}/handling`,
    {
      data: payload,
      method: 'PATCH',
    },
  );
}

export async function completeTicketApi(ticketId: number) {
  return requestClient.post<TicketDetailRecord>(
    `/tickets/${ticketId}/complete`,
  );
}

export async function createTicketCommentApi(ticketId: number, body: string) {
  return requestClient.post<TicketDetailRecord>(
    `/tickets/${ticketId}/comments`,
    { body },
  );
}
