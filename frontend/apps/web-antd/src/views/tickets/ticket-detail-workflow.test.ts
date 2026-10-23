import type { TicketDetailRecord } from '#/api';

import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useTicketDetailWorkflow } from './ticket-detail-workflow';

const api = vi.hoisted(() => ({
  acceptTicketApi: vi.fn(),
  completeTicketApi: vi.fn(),
  createTicketCommentApi: vi.fn(),
  getTicketApi: vi.fn(),
  getUsersApi: vi.fn(),
  rejectTicketApi: vi.fn(),
  updateTicketApi: vi.fn(),
  updateTicketHandlingApi: vi.fn(),
}));

vi.mock('#/api', () => api);

function ticketRecord(overrides: Partial<TicketDetailRecord> = {}) {
  return {
    assignee_display_name: null,
    assignee_user_id: null,
    assignee_username: null,
    body: '正文',
    comments: [],
    completed_at: null,
    created_at: '2026-07-16T00:00:00Z',
    id: 1,
    is_overdue: false,
    planned_completion_at: null,
    priority: null,
    rejection_reason: null,
    status: 'PENDING',
    submitter_display_name: null,
    submitter_user_id: 'user-1',
    submitter_username: 'te1',
    ticket_type: 'REQ',
    title: '标题',
    updated_at: '2026-07-16T00:00:00Z',
    ...overrides,
  } satisfies TicketDetailRecord;
}

describe('ticket detail workflow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('updates the current detail after a successful mutation', async () => {
    const updated = ticketRecord({ status: 'COMPLETED' });
    api.completeTicketApi.mockResolvedValue(updated);
    const workflow = useTicketDetailWorkflow();

    const result = await workflow.complete(1);

    expect(result).toBe('success');
    expect(workflow.ticket.value).toEqual(updated);
    expect(workflow.submitting.value).toBe(false);
  });

  it('reloads the latest detail after a conflict', async () => {
    const latest = ticketRecord({ status: 'ACCEPTED' });
    api.acceptTicketApi.mockRejectedValue({
      response: {
        data: {
          error: {
            code: 'ticket_version_conflict',
            details: null,
            message: '工单已被其他操作更新',
          },
        },
        status: 409,
      },
    });
    api.getTicketApi.mockResolvedValue(latest);
    const workflow = useTicketDetailWorkflow();

    const result = await workflow.accept(1, {
      assignee_user_id: 'admin-1',
      planned_completion_at: '2026-07-17T00:00:00Z',
      priority: 'HIGH',
    });

    expect(result).toBe('conflict');
    expect(api.getTicketApi).toHaveBeenCalledWith(1);
    expect(workflow.ticket.value).toEqual(latest);
    expect(workflow.submitting.value).toBe(false);
  });

  it('does not reload for an unrelated conflict', async () => {
    api.acceptTicketApi.mockRejectedValue({
      response: {
        data: {
          error: {
            code: 'ticket_state_conflict',
            details: null,
            message: '工单状态冲突',
          },
        },
        status: 409,
      },
    });
    const workflow = useTicketDetailWorkflow();

    const result = await workflow.accept(1, {
      assignee_user_id: 'admin-1',
      planned_completion_at: '2026-07-17T00:00:00Z',
      priority: 'HIGH',
    });

    expect(result).toBe('failed');
    expect(api.getTicketApi).not.toHaveBeenCalled();
  });

  it('loads the active administrator list only once', async () => {
    api.getUsersApi.mockResolvedValue([]);
    const workflow = useTicketDetailWorkflow();

    await workflow.loadAdmins();
    await workflow.loadAdmins();

    expect(api.getUsersApi).toHaveBeenCalledTimes(1);
  });
});
