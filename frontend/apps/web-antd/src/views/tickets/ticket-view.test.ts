import { describe, expect, it } from 'vitest';

import {
  activeAdminOptions,
  canCommentOnTicket,
  canEditTicketContent,
  ticketPriorityLabel,
  ticketStatusLabel,
  userDisplayName,
} from './ticket-view';

describe('ticket view helpers', () => {
  it('renders overdue as a derived status', () => {
    expect(ticketStatusLabel({ is_overdue: true, status: 'ACCEPTED' })).toBe(
      '已逾期',
    );
    expect(ticketPriorityLabel('HIGH')).toBe('高');
  });

  it('uses display name before username', () => {
    expect(userDisplayName('管理员', 'admin')).toBe('管理员');
    expect(userDisplayName(null, 'admin')).toBe('admin');
  });

  it('only exposes active administrators as assignees', () => {
    expect(
      activeAdminOptions([
        {
          created_at: '',
          display_name: '管理员',
          id: '1',
          is_active: true,
          last_login_at: null,
          role: 'ADMIN',
          username: 'admin',
        },
        {
          created_at: '',
          display_name: null,
          id: '2',
          is_active: true,
          last_login_at: null,
          role: 'TE',
          username: 'te1',
        },
      ]),
    ).toEqual([{ label: '管理员', value: '1' }]);
  });

  it('keeps content editing and commenting permissions distinct', () => {
    expect(
      canEditTicketContent({
        currentUserId: 'submitter',
        isAdmin: false,
        ticket: { status: 'PENDING', submitter_user_id: 'submitter' },
      }),
    ).toBe(true);
    expect(
      canEditTicketContent({
        currentUserId: 'submitter',
        isAdmin: true,
        ticket: { status: 'PENDING', submitter_user_id: 'submitter' },
      }),
    ).toBe(false);
    expect(
      canCommentOnTicket({
        currentUserId: 'assignee',
        isAdmin: false,
        ticket: {
          assignee_user_id: 'assignee',
          submitter_user_id: 'submitter',
        },
      }),
    ).toBe(true);
  });
});
