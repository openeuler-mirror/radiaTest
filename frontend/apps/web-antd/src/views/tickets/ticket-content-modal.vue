<script lang="ts" setup>
import type { TicketType } from '#/api';

import { reactive, ref, watch } from 'vue';

import { Form, FormItem, Input, Modal, Select } from 'ant-design-vue';

interface ValidatableForm {
  validate: () => Promise<void>;
}

const props = withDefaults(
  defineProps<{
    body?: string;
    editing?: boolean;
    loading?: boolean;
    open: boolean;
    ticketType?: TicketType;
    title?: string;
  }>(),
  {
    body: '',
    editing: false,
    loading: false,
    ticketType: 'REQ',
    title: '',
  },
);

const emit = defineEmits<{
  cancel: [];
  submit: [payload: { body: string; ticket_type: TicketType; title: string }];
}>();

const formRef = ref<null | ValidatableForm>(null);
const form = reactive({
  body: '',
  ticket_type: 'REQ' as TicketType,
  title: '',
});

watch(
  () => props.open,
  (open) => {
    if (!open) return;
    form.ticket_type = props.ticketType;
    form.title = props.title;
    form.body = props.body;
  },
  { immediate: true },
);

async function submit() {
  await formRef.value?.validate();
  emit('submit', {
    body: form.body,
    ticket_type: form.ticket_type,
    title: form.title,
  });
}
</script>

<template>
  <Modal
    :confirm-loading="loading"
    :open="open"
    :title="editing ? '编辑工单' : '提交工单'"
    @cancel="$emit('cancel')"
    @ok="submit"
  >
    <Form ref="formRef" layout="vertical" :model="form">
      <FormItem
        v-if="!editing"
        label="类型"
        name="ticket_type"
        :rules="[{ required: true, message: '请选择工单类型' }]"
      >
        <Select
          v-model:value="form.ticket_type"
          :options="[
            { label: 'REQ', value: 'REQ' },
            { label: 'BUG', value: 'BUG' },
          ]"
        />
      </FormItem>
      <FormItem
        label="标题"
        name="title"
        :rules="[
          { required: true, whitespace: true, message: '请输入标题' },
          { max: 120, message: '标题最多 120 个字符' },
        ]"
      >
        <Input v-model:value="form.title" :maxlength="120" />
      </FormItem>
      <FormItem
        label="正文"
        name="body"
        :rules="[
          { required: true, whitespace: true, message: '请输入正文' },
          { max: 10000, message: '正文最多 10000 个字符' },
        ]"
      >
        <Input.TextArea
          v-model:value="form.body"
          :auto-size="{ minRows: 8, maxRows: 18 }"
          :maxlength="10000"
        />
      </FormItem>
    </Form>
  </Modal>
</template>
