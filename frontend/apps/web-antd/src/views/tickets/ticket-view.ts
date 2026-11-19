import type {
  TicketPriority,
  TicketRecord,
  TicketStatus,
  UserRecord,
} from '#/api';

export const ticketStatusOptions: Array<{
  label: string;
  value: TicketStatus;
}> = [
  { label: '待处理', value: 'PENDING' },
  { label: '已接受', value: 'ACCEPTED' },
  { label: '已拒绝', value: 'REJECTED' },
  { label: '已完成', value: 'COMPLETED' },
];

export const ticketPriorityOptions: Array<{
  label: string;
  value: TicketPriority;
}> = [
  { label: '高', value: 'HIGH' },
  { label: '中', value: 'MEDIUM' },
  { label: '低', value: 'LOW' },
];

export function ticketStatusLabel(
  record: Pick<TicketRecord, 'is_overdue' | 'status'>,
) {
  if (record.is_overdue) return '已逾期';
  return (
    ticketStatusOptions.find((item) => item.value === record.status)?.label ??
    record.status
  );
}

export function ticketStatusColor(
  record: Pick<TicketRecord, 'is_overdue' | 'status'>,
) {
  if (record.is_overdue) return 'orange';
  if (record.status === 'PENDING') return 'blue';
  if (record.status === 'ACCEPTED') return 'cyan';
  if (record.status === 'REJECTED') return 'red';
  return 'green';
}

export function ticketPriorityLabel(priority: null | TicketPriority) {
  if (!priority) return '-';
  return (
    ticketPriorityOptions.find((item) => item.value === priority)?.label ??
    priority
  );
}

export function userDisplayName(
  displayName: null | string,
  username: null | string,
) {
  return displayName || username || '-';
}

export function activeAdminOptions(users: UserRecord[]) {
  return users
    .filter((user) => user.role === 'ADMIN' && user.is_active)
    .map((user) => ({
      label: userDisplayName(user.display_name, user.username),
      value: user.id,
    }));
}

export function canEditTicketContent({
  currentUserId,
  isAdmin,
  ticket,
}: {
  currentUserId?: string;
  isAdmin: boolean;
  ticket: Pick<TicketRecord, 'status' | 'submitter_user_id'>;
}) {
  return (
    !isAdmin &&
    ticket.status === 'PENDING' &&
    ticket.submitter_user_id === currentUserId
  );
}

export function canCommentOnTicket({
  currentUserId,
  isAdmin,
  ticket,
}: {
  currentUserId?: string;
  isAdmin: boolean;
  ticket: Pick<TicketRecord, 'assignee_user_id' | 'submitter_user_id'>;
}) {
  return (
    isAdmin ||
    ticket.submitter_user_id === currentUserId ||
    ticket.assignee_user_id === currentUserId
  );
}

export function formatTicketTime(value: null | string) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}
