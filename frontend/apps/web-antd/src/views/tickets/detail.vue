<script lang="ts" setup>
import type { Dayjs } from 'dayjs';

import type { TicketMutationResult } from './ticket-detail-workflow';

import type {
  TicketHandlingPayload,
  TicketPriority,
  TicketType,
  UserRole,
} from '#/api';

import { computed, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { useTabs } from '@vben/hooks';
import {
  ArrowLeft,
  Check,
  MessageSquareCode,
  Pencil,
  RotateCw,
  X,
} from '@vben/icons';
import { useUserStore } from '@vben/stores';

import {
  Button,
  Card,
  DatePicker,
  Descriptions,
  DescriptionsItem,
  Form,
  FormItem,
  Input,
  message,
  Modal,
  Select,
  Tag,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import TicketContentModal from './ticket-content-modal.vue';
import { useTicketDetailWorkflow } from './ticket-detail-workflow';
import {
  activeAdminOptions,
  canCommentOnTicket,
  canEditTicketContent,
  formatTicketTime,
  ticketPriorityLabel,
  ticketPriorityOptions,
  ticketStatusColor,
  ticketStatusLabel,
  userDisplayName,
} from './ticket-view';

interface ValidatableForm {
  validate: () => Promise<void>;
}

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const { setTabTitle } = useTabs();
const {
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
} = useTicketDetailWorkflow();
const contentOpen = ref(false);
const handlingOpen = ref(false);
const handlingMode = ref<'accept' | 'edit'>('accept');
const rejectOpen = ref(false);
const commentBody = ref('');
const handlingFormRef = ref<null | ValidatableForm>(null);
const rejectFormRef = ref<null | ValidatableForm>(null);
const ticketId = computed(() => Number(route.params.ticketId));
const currentUserId = computed(() => userStore.userInfo?.userId);
const currentRole = computed(
  () => userStore.userInfo?.roles?.[0] as undefined | UserRole,
);
const isAdmin = computed(() => currentRole.value === 'ADMIN');
const canEditContent = computed(
  () =>
    !!ticket.value &&
    canEditTicketContent({
      currentUserId: currentUserId.value,
      isAdmin: isAdmin.value,
      ticket: ticket.value,
    }),
);
const canComment = computed(
  () =>
    !!ticket.value &&
    canCommentOnTicket({
      currentUserId: currentUserId.value,
      isAdmin: isAdmin.value,
      ticket: ticket.value,
    }),
);
const adminOptions = computed(() => activeAdminOptions(admins.value));

const handlingForm = reactive({
  assignee_user_id: '',
  planned_completion_at: undefined as Dayjs | undefined,
  priority: 'MEDIUM' as TicketPriority,
});
const rejectForm = reactive({ reason: '' });

async function loadDetail() {
  if (!Number.isInteger(ticketId.value) || ticketId.value < 1) {
    message.error('工单 ID 无效');
    await router.replace('/tickets');
    return;
  }
  const detail = await loadTicket(ticketId.value);
  void setTabTitle(`工单 #${detail.id}`);
}

function openHandling(mode: 'accept' | 'edit') {
  if (!ticket.value) return;
  handlingMode.value = mode;
  handlingForm.priority = ticket.value.priority ?? 'MEDIUM';
  handlingForm.assignee_user_id = ticket.value.assignee_user_id ?? '';
  handlingForm.planned_completion_at = ticket.value.planned_completion_at
    ? dayjs(ticket.value.planned_completion_at)
    : undefined;
  if (isAdmin.value) void loadAdmins();
  handlingOpen.value = true;
}

function mutationSucceeded(result: TicketMutationResult) {
  if (result === 'conflict') {
    message.warning('工单已更新，已重新读取最新内容');
  }
  return result === 'success';
}

async function submitContent(payload: {
  body: string;
  ticket_type: TicketType;
  title: string;
}) {
  const succeeded = mutationSucceeded(
    await updateContent(ticketId.value, {
      body: payload.body,
      title: payload.title,
    }),
  );
  if (succeeded) {
    message.success('工单内容已更新');
    contentOpen.value = false;
  }
}

async function submitHandling() {
  await handlingFormRef.value?.validate();
  if (!handlingForm.planned_completion_at) return;
  const payload: TicketHandlingPayload = {
    assignee_user_id: handlingForm.assignee_user_id,
    planned_completion_at: handlingForm.planned_completion_at.toISOString(),
    priority: handlingForm.priority,
  };
  const succeeded = mutationSucceeded(
    await (handlingMode.value === 'accept'
      ? accept(ticketId.value, payload)
      : updateHandling(ticketId.value, payload)),
  );
  if (succeeded) {
    message.success(
      handlingMode.value === 'accept' ? '工单已接受' : '处理信息已更新',
    );
    handlingOpen.value = false;
  }
}

async function submitReject() {
  await rejectFormRef.value?.validate();
  const succeeded = mutationSucceeded(
    await reject(ticketId.value, rejectForm.reason),
  );
  if (succeeded) {
    message.success('工单已拒绝');
    rejectOpen.value = false;
  }
}

function confirmComplete() {
  Modal.confirm({
    content: '确认将该工单标记为已完成？',
    onOk: async () => {
      const succeeded = mutationSucceeded(await complete(ticketId.value));
      if (succeeded) message.success('工单已完成');
    },
    title: '确认完成',
  });
}

async function submitComment() {
  if (!commentBody.value.trim()) {
    message.warning('请输入评论内容');
    return;
  }
  const succeeded = mutationSucceeded(
    await addComment(ticketId.value, commentBody.value),
  );
  if (succeeded) {
    commentBody.value = '';
    message.success('评论已提交');
  }
}

watch(ticketId, () => void loadDetail(), { immediate: true });
</script>

<template>
  <Page :title="ticket ? `工单 #${ticket.id}` : `工单 #${ticketId}`">
    <div class="min-w-0 space-y-4">
      <div class="management-toolbar">
        <Button @click="router.push('/tickets')">
          <template #icon><ArrowLeft class="size-4" /></template>
          返回工单列表
        </Button>
        <div class="management-toolbar__actions management-toolbar__group">
          <Button :loading="loading" @click="loadDetail">
            <template #icon><RotateCw class="size-4" /></template>
            刷新
          </Button>
          <Button v-if="canEditContent" @click="contentOpen = true">
            <template #icon><Pencil class="size-4" /></template>
            编辑内容
          </Button>
          <template v-if="isAdmin && ticket?.status === 'PENDING'">
            <Button type="primary" @click="openHandling('accept')">
              <template #icon><Check class="size-4" /></template>
              接受
            </Button>
            <Button danger @click="rejectOpen = true">
              <template #icon><X class="size-4" /></template>
              拒绝
            </Button>
          </template>
          <template v-if="isAdmin && ticket?.status === 'ACCEPTED'">
            <Button @click="openHandling('edit')">
              <template #icon><Pencil class="size-4" /></template>
              编辑处理信息
            </Button>
            <Button type="primary" @click="confirmComplete">
              <template #icon><Check class="size-4" /></template>
              标记完成
            </Button>
          </template>
        </div>
      </div>

      <Card v-if="ticket" :loading="loading">
        <div class="min-w-0 space-y-5">
          <Descriptions bordered :column="1" size="small">
            <DescriptionsItem label="序号">{{ ticket.id }}</DescriptionsItem>
            <DescriptionsItem label="类型">
              <Tag :color="ticket.ticket_type === 'BUG' ? 'red' : 'blue'">
                {{ ticket.ticket_type }}
              </Tag>
            </DescriptionsItem>
            <DescriptionsItem label="标题">
              <span class="break-words">{{ ticket.title }}</span>
            </DescriptionsItem>
            <DescriptionsItem label="提出人">
              {{
                userDisplayName(
                  ticket.submitter_display_name,
                  ticket.submitter_username,
                )
              }}
            </DescriptionsItem>
            <DescriptionsItem label="状态">
              <Tag :color="ticketStatusColor(ticket)">
                {{ ticketStatusLabel(ticket) }}
              </Tag>
            </DescriptionsItem>
            <DescriptionsItem label="优先级">
              {{ ticketPriorityLabel(ticket.priority) }}
            </DescriptionsItem>
            <DescriptionsItem label="责任人">
              {{
                userDisplayName(
                  ticket.assignee_display_name,
                  ticket.assignee_username,
                )
              }}
            </DescriptionsItem>
            <DescriptionsItem label="计划完成时间">
              {{ formatTicketTime(ticket.planned_completion_at) }}
            </DescriptionsItem>
            <DescriptionsItem label="实际完成时间">
              {{ formatTicketTime(ticket.completed_at) }}
            </DescriptionsItem>
            <DescriptionsItem label="创建时间">
              {{ formatTicketTime(ticket.created_at) }}
            </DescriptionsItem>
            <DescriptionsItem label="最后更新时间">
              {{ formatTicketTime(ticket.updated_at) }}
            </DescriptionsItem>
            <DescriptionsItem v-if="ticket.rejection_reason" label="拒绝理由">
              <span class="whitespace-pre-wrap break-words">
                {{ ticket.rejection_reason }}
              </span>
            </DescriptionsItem>
            <DescriptionsItem label="正文">
              <span class="whitespace-pre-wrap break-words">
                {{ ticket.body }}
              </span>
            </DescriptionsItem>
          </Descriptions>

          <section class="space-y-4 border-t border-border pt-4">
            <div class="text-base font-semibold">评论</div>
            <div
              v-if="ticket.comments.length === 0"
              class="text-sm text-muted-foreground"
            >
              暂无评论
            </div>
            <div
              v-for="comment in ticket.comments"
              :key="comment.id"
              class="space-y-2 border-b border-border pb-4 last:border-b-0"
            >
              <div class="management-toolbar">
                <span class="font-medium">
                  {{
                    userDisplayName(
                      comment.author_display_name,
                      comment.author_username,
                    )
                  }}
                </span>
                <span class="text-xs text-muted-foreground">
                  {{ formatTicketTime(comment.created_at) }}
                </span>
              </div>
              <div class="whitespace-pre-wrap break-words text-sm">
                {{ comment.body }}
              </div>
            </div>

            <div v-if="canComment" class="space-y-3">
              <Input.TextArea
                v-model:value="commentBody"
                :auto-size="{ minRows: 3, maxRows: 10 }"
                :maxlength="5000"
                placeholder="发表评论"
              />
              <div class="flex justify-end">
                <Button
                  :loading="submitting"
                  type="primary"
                  @click="submitComment"
                >
                  <template #icon>
                    <MessageSquareCode class="size-4" />
                  </template>
                  提交评论
                </Button>
              </div>
            </div>
          </section>
        </div>
      </Card>
    </div>

    <TicketContentModal
      v-if="ticket"
      :body="ticket.body"
      editing
      :loading="submitting"
      :open="contentOpen"
      :ticket-type="ticket.ticket_type"
      :title="ticket.title"
      @cancel="contentOpen = false"
      @submit="submitContent"
    />

    <Modal
      :confirm-loading="submitting"
      :open="handlingOpen"
      :title="handlingMode === 'accept' ? '接受工单' : '编辑处理信息'"
      @cancel="handlingOpen = false"
      @ok="submitHandling"
    >
      <Form ref="handlingFormRef" layout="vertical" :model="handlingForm">
        <FormItem
          label="优先级"
          name="priority"
          :rules="[{ required: true, message: '请选择优先级' }]"
        >
          <Select
            v-model:value="handlingForm.priority"
            :options="ticketPriorityOptions"
          />
        </FormItem>
        <FormItem
          label="责任人"
          name="assignee_user_id"
          :rules="[{ required: true, message: '请选择责任人' }]"
        >
          <Select
            v-model:value="handlingForm.assignee_user_id"
            :loading="isAdmin && admins.length === 0"
            :options="adminOptions"
          />
        </FormItem>
        <FormItem
          label="计划完成时间"
          name="planned_completion_at"
          :rules="[{ required: true, message: '请选择计划完成时间' }]"
        >
          <DatePicker
            v-model:value="handlingForm.planned_completion_at"
            class="w-full"
            show-time
          />
        </FormItem>
      </Form>
    </Modal>

    <Modal
      :confirm-loading="submitting"
      :open="rejectOpen"
      title="拒绝工单"
      @cancel="rejectOpen = false"
      @ok="submitReject"
    >
      <Form ref="rejectFormRef" layout="vertical" :model="rejectForm">
        <FormItem
          label="拒绝理由"
          name="reason"
          :rules="[
            { required: true, whitespace: true, message: '请输入拒绝理由' },
            { max: 2000, message: '拒绝理由最多 2000 个字符' },
          ]"
        >
          <Input.TextArea
            v-model:value="rejectForm.reason"
            :auto-size="{ minRows: 5, maxRows: 12 }"
            :maxlength="2000"
          />
        </FormItem>
      </Form>
    </Modal>
  </Page>
</template>
