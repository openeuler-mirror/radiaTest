import type {
  TicketContentUpdatePayload,
  TicketDetailRecord,
  TicketHandlingPayload,
  UserRecord,
} from '#/api';

import { ref } from 'vue';

import {
  acceptTicketApi,
  completeTicketApi,
  createTicketCommentApi,
  getTicketApi,
  getUsersApi,
  rejectTicketApi,
  updateTicketApi,
  updateTicketHandlingApi,
} from '#/api';
import { parseAPIError } from '#/api/api-error';

export type TicketMutationResult = 'conflict' | 'failed' | 'success';

export function useTicketDetailWorkflow() {
  const ticket = ref<null | TicketDetailRecord>(null);
  const admins = ref<UserRecord[]>([]);
  const loading = ref(false);
  const submitting = ref(false);
  const adminsLoaded = ref(false);

  async function loadTicket(ticketId: number) {
    loading.value = true;
    try {
      ticket.value = await getTicketApi(ticketId);
      return ticket.value;
    } finally {
      loading.value = false;
    }
  }

  async function loadAdmins() {
    if (adminsLoaded.value) return admins.value;
    admins.value = await getUsersApi({
      is_active: true,
      limit: 200,
      role: 'ADMIN',
    });
    adminsLoaded.value = true;
    return admins.value;
  }

  async function runMutation(
    ticketId: number,
    operation: () => Promise<TicketDetailRecord>,
  ): Promise<TicketMutationResult> {
    submitting.value = true;
    try {
      ticket.value = await operation();
      return 'success';
    } catch (error) {
      if (parseAPIError(error)?.code === 'ticket_version_conflict') {
        await loadTicket(ticketId);
        return 'conflict';
      }
      return 'failed';
    } finally {
      submitting.value = false;
    }
  }

  function updateContent(
    ticketId: number,
    payload: TicketContentUpdatePayload,
  ) {
    return runMutation(ticketId, () => updateTicketApi(ticketId, payload));
  }

  function accept(ticketId: number, payload: TicketHandlingPayload) {
    return runMutation(ticketId, () => acceptTicketApi(ticketId, payload));
  }

  function updateHandling(
    ticketId: number,
    payload: Partial<TicketHandlingPayload>,
  ) {
    return runMutation(ticketId, () =>
      updateTicketHandlingApi(ticketId, payload),
    );
  }

  function reject(ticketId: number, reason: string) {
    return runMutation(ticketId, () => rejectTicketApi(ticketId, reason));
  }

  function complete(ticketId: number) {
    return runMutation(ticketId, () => completeTicketApi(ticketId));
  }

  function addComment(ticketId: number, body: string) {
    return runMutation(ticketId, () => createTicketCommentApi(ticketId, body));
  }

  return {
    accept,
    addComment,
    admins,
    complete,
    loadAdmins,
    loading,
    loadTicket,
    reject,
    submitting,
    ticket,
    updateContent,
    updateHandling,
  };
}
