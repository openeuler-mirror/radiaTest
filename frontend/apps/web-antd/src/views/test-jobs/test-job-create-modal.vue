<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import type {
  MugenCaseRecord,
  TestJobDetailRecord,
  TestJobTemplateRecord,
  VMImageRecord,
} from '#/api';

import { computed, reactive, ref, watch } from 'vue';

import {
  Button,
  Checkbox,
  Input,
  InputNumber,
  message,
  Modal,
  Select,
  Tag,
  Textarea,
} from 'ant-design-vue';

import {
  createTestJobApi,
  createTestJobTemplateApi,
  updateTestJobTemplateApi,
} from '#/api';

import {
  buildCaseSelections,
  buildTemplateJobName,
  buildTestJobPayload,
  buildTestJobTemplatePatch,
  findUnavailableCaseSelections,
  groupCasesBySuite,
  inferSelectionConstraints,
  isCaseSelectable,
  isValidTestJobTemplateName,
  uniqueOptions,
  validateTestJobForm,
} from './test-job-view';

const props = defineProps<{
  cases: MugenCaseRecord[];
  images: VMImageRecord[];
  purpose?: 'create-job' | 'create-template' | 'edit-template';
  template?: null | TestJobTemplateRecord;
}>();

const emit = defineEmits<{
  jobCreated: [job: TestJobDetailRecord];
  templateSaved: [template: TestJobTemplateRecord];
}>();

const open = defineModel<boolean>('open', { required: true });
const submitting = ref(false);
const hydrating = ref(false);
const activeSuite = ref('');
const suiteFilter = ref('');
const caseFilter = ref('');
const submitIdempotencyKey = ref(createIdempotencyKey());
const selectedCaseNames = reactive<Record<string, string[]>>({});

const form = reactive({
  arch: '',
  dist: 'openEuler',
  envSetNum: 1,
  imageRound: '',
  keepFailedEnv: false,
  name: '',
  osVersion: '',
  postEnvScript: '',
  preEnvScript: '',
});

const groupedCases = computed(() => groupCasesBySuite(props.cases));
const suites = computed(() => [...groupedCases.value.keys()]);
const filteredSuites = computed(() => {
  const keyword = suiteFilter.value.trim().toLocaleLowerCase();
  return keyword
    ? suites.value.filter((suite) =>
        suite.toLocaleLowerCase().includes(keyword),
      )
    : suites.value;
});
const activeCases = computed(
  () => groupedCases.value.get(activeSuite.value) ?? [],
);
const filteredCases = computed(() => {
  const keyword = caseFilter.value.trim().toLocaleLowerCase();
  return keyword
    ? activeCases.value.filter((item) =>
        item.case_name.toLocaleLowerCase().includes(keyword),
      )
    : activeCases.value;
});
const selections = computed(() => buildCaseSelections(selectedCaseNames));
const constraints = computed(() =>
  inferSelectionConstraints(props.cases, selections.value),
);
const purpose = computed(() => props.purpose ?? 'create-job');
const isTemplatePurpose = computed(() => purpose.value !== 'create-job');
const modalTitle = computed(() => {
  if (purpose.value === 'create-template') return '创建任务模板';
  if (purpose.value === 'edit-template') return '编辑任务模板';
  return '创建测试任务';
});
const unavailableSelections = computed(() =>
  findUnavailableCaseSelections(props.cases, selections.value),
);

const distOptions = computed(() =>
  uniqueOptions(props.images.map((image) => image.dist)),
);
const osVersionOptions = computed(() =>
  uniqueOptions(
    props.images
      .filter((image) => image.dist === form.dist)
      .map((image) => image.os_version),
  ),
);
const roundOptions = computed(() =>
  uniqueOptions(
    props.images
      .filter(
        (image) =>
          image.dist === form.dist && image.os_version === form.osVersion,
      )
      .map((image) => image.image_round),
  ),
);
const archOptions = computed(() =>
  uniqueOptions(
    props.images
      .filter(
        (image) =>
          image.dist === form.dist &&
          image.os_version === form.osVersion &&
          image.image_round === form.imageRound,
      )
      .map((image) => image.arch),
  ),
);

function createIdempotencyKey() {
  return `test-job-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function clearSelections() {
  for (const key of Object.keys(selectedCaseNames)) {
    delete selectedCaseNames[key];
  }
}

function setSelections(items: TestJobTemplateRecord['cases']) {
  clearSelections();
  for (const selection of items) {
    selectedCaseNames[selection.suite_name] = [...(selection.case_names ?? [])];
  }
}

function removeUnavailableSelections() {
  const selectable = new Set(
    props.cases
      .filter(isCaseSelectable)
      .map((item) => `${item.suite_name}\0${item.case_name}`),
  );
  for (const [suite, caseNames] of Object.entries(selectedCaseNames)) {
    selectedCaseNames[suite] = caseNames.filter((caseName) =>
      selectable.has(`${suite}\0${caseName}`),
    );
  }
}

function syncImageSelection() {
  if (!distOptions.value.some((item) => item.value === form.dist)) {
    form.dist = String(distOptions.value[0]?.value ?? '');
  }
  if (!osVersionOptions.value.some((item) => item.value === form.osVersion)) {
    form.osVersion = String(osVersionOptions.value[0]?.value ?? '');
  }
  if (!roundOptions.value.some((item) => item.value === form.imageRound)) {
    form.imageRound = String(roundOptions.value[0]?.value ?? '');
  }
  if (!archOptions.value.some((item) => item.value === form.arch)) {
    form.arch = String(archOptions.value[0]?.value ?? '');
  }
}

function resetForm() {
  hydrating.value = true;
  submitIdempotencyKey.value = createIdempotencyKey();
  suiteFilter.value = '';
  caseFilter.value = '';
  const template = props.template;
  if (template) {
    form.name =
      purpose.value === 'create-job'
        ? buildTemplateJobName(template.name, new Date())
        : template.name;
    form.envSetNum = template.env_set_num;
    form.keepFailedEnv = template.keep_failed_env;
    form.preEnvScript = template.pre_env_script ?? '';
    form.postEnvScript = template.post_env_script ?? '';
    form.dist = template.dist;
    form.osVersion = template.os_version;
    form.imageRound = template.image_round;
    form.arch = template.arch;
    setSelections(template.cases);
    activeSuite.value =
      template.cases.find((item) => groupedCases.value.has(item.suite_name))
        ?.suite_name ??
      suites.value[0] ??
      '';
  } else {
    form.name = '';
    form.envSetNum = 1;
    form.keepFailedEnv = false;
    form.preEnvScript = '';
    form.postEnvScript = '';
    form.dist = 'openEuler';
    form.osVersion = '';
    form.imageRound = '';
    form.arch = '';
    clearSelections();
    activeSuite.value = suites.value[0] ?? '';
    syncImageSelection();
  }
  hydrating.value = false;
}

function selectedNames(suite: string) {
  return selectedCaseNames[suite] ?? [];
}

function suiteSelectedCount(suite: string) {
  return selectedNames(suite).length;
}

function suiteChecked(suite: string) {
  const total = selectableCases(suite).length;
  return total > 0 && suiteSelectedCount(suite) === total;
}

function suiteIndeterminate(suite: string) {
  const selected = suiteSelectedCount(suite);
  const total = selectableCases(suite).length;
  return selected > 0 && selected < total;
}

function selectableCases(suite: string) {
  return (groupedCases.value.get(suite) ?? []).filter(isCaseSelectable);
}

function toggleSuite(suite: string, checked: boolean) {
  selectedCaseNames[suite] = checked
    ? selectableCases(suite).map((item) => item.case_name)
    : [];
}

function caseChecked(caseName: string) {
  return selectedNames(activeSuite.value).includes(caseName);
}

function toggleCase(caseName: string, checked: boolean) {
  const names = new Set(selectedNames(activeSuite.value));
  if (checked) names.add(caseName);
  else names.delete(caseName);
  selectedCaseNames[activeSuite.value] = [...names];
}

async function submit() {
  const error = validateTestJobForm(form, selections.value);
  if (error) {
    message.warning(error);
    return;
  }
  if (isTemplatePurpose.value && !isValidTestJobTemplateName(form.name)) {
    message.warning('模板名称只允许字母、数字、点、连字符和下划线');
    return;
  }
  if (
    unavailableSelections.value.length > 0 &&
    purpose.value !== 'edit-template'
  ) {
    message.warning('请先移除当前不可用的用例');
    return;
  }
  submitting.value = true;
  try {
    const payload = buildTestJobPayload(form, selections.value);
    if (purpose.value === 'create-job') {
      const job = await createTestJobApi(payload, submitIdempotencyKey.value);
      message.success('测试任务已创建');
      emit('jobCreated', job);
    } else if (purpose.value === 'edit-template' && props.template) {
      const template = await updateTestJobTemplateApi(
        props.template.id,
        buildTestJobTemplatePatch(props.template, payload),
      );
      message.success('任务模板已更新');
      emit('templateSaved', template);
    } else {
      const template = await createTestJobTemplateApi(payload);
      message.success('任务模板已创建');
      emit('templateSaved', template);
    }
    open.value = false;
  } finally {
    submitting.value = false;
  }
}

watch(open, (value) => {
  if (value) resetForm();
});
watch(
  () => props.cases,
  () => {
    if (!activeSuite.value) activeSuite.value = suites.value[0] ?? '';
  },
);
watch(
  () => props.images,
  () => {
    if (!props.template) syncImageSelection();
  },
);
watch(
  () => form.dist,
  () => {
    if (hydrating.value) return;
    form.osVersion = '';
    form.imageRound = '';
    form.arch = '';
    syncImageSelection();
  },
);
watch(
  () => form.osVersion,
  () => {
    if (hydrating.value) return;
    form.imageRound = '';
    form.arch = '';
    syncImageSelection();
  },
);
watch(
  () => form.imageRound,
  () => {
    if (hydrating.value) return;
    form.arch = '';
    syncImageSelection();
  },
);
</script>

<template>
  <Modal
    v-model:open="open"
    :confirm-loading="submitting"
    destroy-on-close
    :title="modalTitle"
    width="min(1100px, calc(100vw - 32px))"
    @ok="submit"
  >
    <div class="space-y-5">
      <div class="management-edit-grid">
        <div class="management-edit-grid__full">
          <span
            class="management-filter__label management-filter__label--required"
          >
            {{ isTemplatePurpose ? '模板名称' : '任务名称' }}
          </span>
          <Input
            v-model:value="form.name"
            :maxlength="isTemplatePurpose ? 64 : 128"
          />
        </div>
        <div>
          <span class="management-filter__label">测试框架</span>
          <Select
            :options="[{ label: 'Mugen', value: 'mugen' }]"
            class="w-full"
            disabled
            value="mugen"
          />
        </div>
        <div>
          <span class="management-filter__label">环境类型</span>
          <Select
            :options="[{ label: 'VM', value: 'vm' }]"
            class="w-full"
            disabled
            value="vm"
          />
        </div>
        <div>
          <span
            class="management-filter__label management-filter__label--required"
          >
            发行版
          </span>
          <Select
            v-model:value="form.dist"
            :options="distOptions"
            class="w-full"
          />
        </div>
        <div>
          <span
            class="management-filter__label management-filter__label--required"
          >
            OS 版本
          </span>
          <Select
            v-model:value="form.osVersion"
            :options="osVersionOptions"
            class="w-full"
          />
        </div>
        <div>
          <span
            class="management-filter__label management-filter__label--required"
          >
            轮次
          </span>
          <Select
            v-model:value="form.imageRound"
            :options="roundOptions"
            class="w-full"
          />
        </div>
        <div>
          <span
            class="management-filter__label management-filter__label--required"
          >
            架构
          </span>
          <Select
            v-model:value="form.arch"
            :options="archOptions"
            class="w-full"
          />
        </div>
        <div>
          <span
            class="management-filter__label management-filter__label--required"
          >
            环境套数
          </span>
          <InputNumber
            v-model:value="form.envSetNum"
            :max="20"
            :min="1"
            class="w-full"
          />
        </div>
        <div class="flex items-end pb-1">
          <Checkbox v-model:checked="form.keepFailedEnv">保留失败环境</Checkbox>
        </div>
      </div>

      <section class="space-y-2 border-t border-border pt-4">
        <div class="management-toolbar">
          <span class="text-sm font-semibold">选择 Suite / Case</span>
          <div class="management-toolbar__actions management-toolbar__group">
            <Tag>{{ selections.length }} 个 Suite</Tag>
            <Tag color="blue">{{ constraints.caseCount }} 个 Case</Tag>
            <Tag>最多 {{ constraints.nodeNum }} 节点</Tag>
            <Tag>{{ constraints.addDiskNum }} 块额外数据盘</Tag>
            <Tag>{{ constraints.addNicNum }} 张额外网卡</Tag>
          </div>
        </div>
        <div
          v-if="unavailableSelections.length > 0"
          class="management-toolbar rounded border border-border px-3 py-2"
        >
          <Tag color="orange">
            {{ unavailableSelections.length }} 个已选用例当前不可用
          </Tag>
          <Button size="small" @click="removeUnavailableSelections">
            移除失效用例
          </Button>
        </div>
        <div class="test-case-picker">
          <div class="test-case-picker__pane">
            <Input
              v-model:value="suiteFilter"
              allow-clear
              placeholder="过滤 Suite"
            />
            <div class="test-case-picker__list">
              <div
                v-for="suite in filteredSuites"
                :key="suite"
                class="test-case-picker__row"
                :class="{
                  'test-case-picker__row--active': suite === activeSuite,
                }"
                @click="activeSuite = suite"
              >
                <Checkbox
                  :checked="suiteChecked(suite)"
                  :disabled="selectableCases(suite).length === 0"
                  :indeterminate="suiteIndeterminate(suite)"
                  @click.stop
                  @update:checked="toggleSuite(suite, Boolean($event))"
                />
                <span class="min-w-0 flex-1 truncate">{{ suite }}</span>
                <span class="text-xs text-muted-foreground">
                  {{ suiteSelectedCount(suite) }}/{{
                    selectableCases(suite).length
                  }}
                </span>
              </div>
            </div>
          </div>
          <div class="test-case-picker__pane">
            <Input
              v-model:value="caseFilter"
              allow-clear
              placeholder="过滤 Case"
            />
            <div class="test-case-picker__list">
              <label
                v-for="item in filteredCases"
                :key="item.id"
                class="test-case-picker__row"
              >
                <Checkbox
                  :checked="caseChecked(item.case_name)"
                  :disabled="!isCaseSelectable(item)"
                  @update:checked="toggleCase(item.case_name, Boolean($event))"
                />
                <span class="min-w-0 flex-1 break-all">{{
                  item.case_name
                }}</span>
                <span class="text-xs text-muted-foreground">
                  {{ item.node_num }}N / {{ item.add_disk_num }}D /
                  {{ item.add_nic_num }}NIC
                </span>
                <Tag v-if="!isCaseSelectable(item)">不可选</Tag>
              </label>
            </div>
          </div>
        </div>
      </section>

      <section
        class="grid grid-cols-1 gap-4 border-t border-border pt-4 md:grid-cols-2"
      >
        <div>
          <span class="management-filter__label">环境准备脚本</span>
          <Textarea
            v-model:value="form.preEnvScript"
            :auto-size="{ minRows: 4, maxRows: 10 }"
            placeholder="可选 Bash 脚本"
          />
        </div>
        <div>
          <span class="management-filter__label">环境清理脚本</span>
          <Textarea
            v-model:value="form.postEnvScript"
            :auto-size="{ minRows: 4, maxRows: 10 }"
            placeholder="可选 Bash 脚本"
          />
        </div>
      </section>
    </div>
  </Modal>
</template>

<style scoped>
.test-case-picker {
  display: grid;
  grid-template-columns: minmax(260px, 0.8fr) minmax(320px, 1.2fr);
  gap: 12px;
}

.test-case-picker__pane {
  min-width: 0;
  padding: 12px;
  border: 1px solid hsl(var(--border));
}

.test-case-picker__list {
  height: 300px;
  margin-top: 10px;
  overflow: auto;
}

.test-case-picker__row {
  display: flex;
  gap: 8px;
  align-items: center;
  min-height: 36px;
  padding: 6px 8px;
  cursor: pointer;
}

.test-case-picker__row:hover,
.test-case-picker__row--active {
  background: hsl(var(--accent));
}

@media (max-width: 768px) {
  .test-case-picker {
    grid-template-columns: minmax(0, 1fr);
  }

  .test-case-picker__list {
    height: 220px;
  }
}
</style>
