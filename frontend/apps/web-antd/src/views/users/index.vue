<script lang="ts" setup>
import type { TableColumnsType } from 'ant-design-vue';

import type { UserRecord, UserRole } from '#/api';

import { computed, onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { LockKeyhole, Plus, UserRoundPen } from '@vben/icons';
import { useUserStore } from '@vben/stores';

import {
  Switch as AntSwitch,
  Button,
  Card,
  Form,
  FormItem,
  Input,
  message,
  Modal,
  Select,
  Space,
  Table,
  Tag,
} from 'ant-design-vue';

import {
  createUserApi,
  getUsersApi,
  resetUserPasswordApi,
  updateUserApi,
} from '#/api';

interface ValidatableForm {
  validate: () => Promise<void>;
}

const roles: Array<{ label: string; value: UserRole }> = [
  { label: '管理员', value: 'ADMIN' },
  { label: '测试系统工程师', value: 'TSE' },
  { label: '测试工程师', value: 'TE' },
];

const userStore = useUserStore();
const loading = ref(false);
const creating = ref(false);
const editing = ref(false);
const resetting = ref(false);
const users = ref<UserRecord[]>([]);
const selectedUser = ref<null | UserRecord>(null);
const createOpen = ref(false);
const editOpen = ref(false);
const resetOpen = ref(false);
const createFormRef = ref<null | ValidatableForm>(null);
const editFormRef = ref<null | ValidatableForm>(null);
const resetFormRef = ref<null | ValidatableForm>(null);

const createForm = reactive({
  display_name: '',
  password: '',
  password_confirm: '',
  role: 'TE' as UserRole,
  username: '',
});

const editForm = reactive({
  display_name: '',
  is_active: true,
  role: 'TE' as UserRole,
});

const resetForm = reactive({
  password: '',
  password_confirm: '',
});

const columns: TableColumnsType<UserRecord> = [
  {
    dataIndex: 'username',
    fixed: 'left',
    title: '用户名',
    width: 160,
  },
  {
    dataIndex: 'display_name',
    title: '显示名',
    width: 180,
  },
  {
    dataIndex: 'role',
    title: '角色',
    width: 130,
  },
  {
    dataIndex: 'is_active',
    title: '状态',
    width: 100,
  },
  {
    dataIndex: 'last_login_at',
    title: '最近登录',
    width: 190,
  },
  {
    dataIndex: 'created_at',
    title: '创建时间',
    width: 190,
  },
  {
    fixed: 'right',
    key: 'action',
    title: '',
    width: 190,
  },
];

const currentUserId = computed(() => userStore.userInfo?.userId);

function normalizeOptional(value: string) {
  const trimmed = value.trim();
  return trimmed || null;
}

async function loadUsers() {
  loading.value = true;
  try {
    users.value = await getUsersApi({ limit: 200 });
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  createForm.username = '';
  createForm.display_name = '';
  createForm.role = 'TE';
  createForm.password = '';
  createForm.password_confirm = '';
  createOpen.value = true;
}

async function submitCreate() {
  await createFormRef.value?.validate();
  creating.value = true;
  try {
    await createUserApi({
      display_name: normalizeOptional(createForm.display_name),
      password: createForm.password,
      role: createForm.role,
      username: createForm.username.trim(),
    });
    message.success('用户已创建');
    createOpen.value = false;
    await loadUsers();
  } finally {
    creating.value = false;
  }
}

function openEdit(record: UserRecord) {
  selectedUser.value = record;
  editForm.display_name = record.display_name ?? '';
  editForm.role = record.role;
  editForm.is_active = record.is_active;
  editOpen.value = true;
}

async function submitEdit() {
  if (!selectedUser.value) return;
  await editFormRef.value?.validate();
  if (selectedUser.value.is_active !== editForm.is_active) {
    Modal.confirm({
      content: `确认${editForm.is_active ? '启用' : '禁用'}用户 ${selectedUser.value.username}？`,
      onOk: () => submitEditConfirmed(),
      title: '确认状态变更',
    });
    return;
  }
  await submitEditConfirmed();
}

async function submitEditConfirmed() {
  if (!selectedUser.value) return;
  editing.value = true;
  try {
    await updateUserApi(selectedUser.value.id, {
      display_name: normalizeOptional(editForm.display_name),
      is_active: editForm.is_active,
      role: editForm.role,
    });
    message.success('用户已更新');
    editOpen.value = false;
    await loadUsers();
  } finally {
    editing.value = false;
  }
}

function openResetPassword(record: UserRecord) {
  selectedUser.value = record;
  resetForm.password = '';
  resetForm.password_confirm = '';
  resetOpen.value = true;
}

function asUserRecord(record: Record<string, unknown>) {
  return record as unknown as UserRecord;
}

function validateCreatePasswordConfirm() {
  if (createForm.password_confirm !== createForm.password) {
    return Promise.reject(new Error('两次输入的密码不一致'));
  }
  return Promise.resolve();
}

function validateResetPasswordConfirm() {
  if (resetForm.password_confirm !== resetForm.password) {
    return Promise.reject(new Error('两次输入的密码不一致'));
  }
  return Promise.resolve();
}

async function submitResetPassword() {
  if (!selectedUser.value) return;
  await resetFormRef.value?.validate();
  resetting.value = true;
  try {
    await resetUserPasswordApi(selectedUser.value.id, {
      password: resetForm.password,
    });
    message.success('密码已重置');
    resetOpen.value = false;
  } finally {
    resetting.value = false;
  }
}

function roleLabel(role: UserRole) {
  return roles.find((item) => item.value === role)?.label ?? role;
}

function roleColor(role: UserRole) {
  if (role === 'ADMIN') return 'red';
  if (role === 'TSE') return 'blue';
  return 'green';
}

function formatTime(value: null | string) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function displayValue(value: null | string) {
  return value || '-';
}

onMounted(() => {
  void loadUsers();
});
</script>

<template>
  <Page title="用户管理">
    <div class="space-y-4">
      <Card class="management-table-card" :body-style="{ padding: 0 }">
        <div class="management-toolbar management-toolbar--table">
          <div class="management-toolbar__group">
            <span>用户列表</span>
            <Tag>{{ users.length }}</Tag>
          </div>
          <div class="management-toolbar__actions management-toolbar__group">
            <Button size="small" type="primary" @click="openCreate">
              <template #icon><Plus class="size-4" /></template>
              新建
            </Button>
          </div>
        </div>
        <Table
          :columns="columns"
          :data-source="users"
          :loading="loading"
          :pagination="false"
          :scroll="{ x: 1050 }"
          row-key="id"
          size="small"
        >
          <template #bodyCell="{ column, record, text }">
            <template v-if="column.dataIndex === 'role'">
              <Tag :color="roleColor(record.role)">
                {{ roleLabel(record.role) }}
              </Tag>
            </template>
            <template v-else-if="column.dataIndex === 'is_active'">
              <Tag :color="record.is_active ? 'green' : 'default'">
                {{ record.is_active ? '启用' : '禁用' }}
              </Tag>
            </template>
            <template v-else-if="column.dataIndex === 'last_login_at'">
              {{ formatTime(record.last_login_at) }}
            </template>
            <template v-else-if="column.dataIndex === 'created_at'">
              {{ formatTime(record.created_at) }}
            </template>
            <template v-else-if="column.key === 'action'">
              <Space>
                <Button
                  size="small"
                  type="link"
                  @click="openEdit(asUserRecord(record))"
                >
                  <template #icon>
                    <UserRoundPen class="size-4" />
                  </template>
                  编辑
                </Button>
                <Button
                  :disabled="record.id === currentUserId"
                  size="small"
                  type="link"
                  @click="openResetPassword(asUserRecord(record))"
                >
                  <template #icon>
                    <LockKeyhole class="size-4" />
                  </template>
                  重置密码
                </Button>
              </Space>
            </template>
            <template v-else>
              {{ displayValue(text) }}
            </template>
          </template>
        </Table>
      </Card>
    </div>

    <Modal
      v-model:open="createOpen"
      :confirm-loading="creating"
      destroy-on-close
      title="新建用户"
      @ok="submitCreate"
    >
      <Form
        ref="createFormRef"
        :model="createForm"
        layout="vertical"
        class="pt-2"
      >
        <FormItem
          label="用户名"
          name="username"
          :rules="[
            { required: true, message: '请输入用户名' },
            {
              pattern: /^[a-z0-9]{3,64}$/,
              message: '仅允许 3-64 位小写字母和数字',
            },
          ]"
        >
          <Input v-model:value="createForm.username" />
        </FormItem>
        <FormItem label="显示名" name="display_name">
          <Input v-model:value="createForm.display_name" />
        </FormItem>
        <FormItem
          label="角色"
          name="role"
          :rules="[{ required: true, message: '请选择角色' }]"
        >
          <Select v-model:value="createForm.role" :options="roles" />
        </FormItem>
        <FormItem
          label="密码"
          name="password"
          :rules="[
            { required: true, message: '请输入密码' },
            { min: 8, message: '密码至少 8 位' },
          ]"
        >
          <Input v-model:value="createForm.password" type="password" />
        </FormItem>
        <FormItem
          label="确认密码"
          name="password_confirm"
          :rules="[
            { required: true, message: '请再次输入密码' },
            { validator: validateCreatePasswordConfirm },
          ]"
        >
          <Input v-model:value="createForm.password_confirm" type="password" />
        </FormItem>
      </Form>
    </Modal>

    <Modal
      v-model:open="editOpen"
      :confirm-loading="editing"
      destroy-on-close
      title="编辑用户"
      @ok="submitEdit"
    >
      <Form ref="editFormRef" :model="editForm" layout="vertical" class="pt-2">
        <FormItem label="显示名" name="display_name">
          <Input v-model:value="editForm.display_name" />
        </FormItem>
        <FormItem
          label="角色"
          name="role"
          :rules="[{ required: true, message: '请选择角色' }]"
        >
          <Select v-model:value="editForm.role" :options="roles" />
        </FormItem>
        <FormItem label="状态" name="is_active">
          <AntSwitch
            v-model:checked="editForm.is_active"
            checked-children="启用"
            un-checked-children="禁用"
          />
        </FormItem>
      </Form>
    </Modal>

    <Modal
      v-model:open="resetOpen"
      :confirm-loading="resetting"
      destroy-on-close
      title="重置密码"
      @ok="submitResetPassword"
    >
      <Form
        ref="resetFormRef"
        :model="resetForm"
        layout="vertical"
        class="pt-2"
      >
        <FormItem label="用户名">
          {{ selectedUser?.username }}
        </FormItem>
        <FormItem
          label="新密码"
          name="password"
          :rules="[
            { required: true, message: '请输入新密码' },
            { min: 8, message: '密码至少 8 位' },
          ]"
        >
          <Input v-model:value="resetForm.password" type="password" />
        </FormItem>
        <FormItem
          label="确认密码"
          name="password_confirm"
          :rules="[
            { required: true, message: '请再次输入新密码' },
            { validator: validateResetPasswordConfirm },
          ]"
        >
          <Input v-model:value="resetForm.password_confirm" type="password" />
        </FormItem>
      </Form>
    </Modal>
  </Page>
</template>
