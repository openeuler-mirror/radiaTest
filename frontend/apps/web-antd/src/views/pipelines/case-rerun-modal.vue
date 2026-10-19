<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import type { PipelineRerunCandidateRecord, PipelineRunJobRecord } from '#/api';

import { computed, ref } from 'vue';

import {
  Alert,
  Button,
  Checkbox,
  Input,
  message,
  Modal,
  Select,
  SelectOption,
  Tag,
  Tooltip,
} from 'ant-design-vue';

import { rerunRunJobCasesApi } from '#/api';

import {
  defaultRerunCaseIds,
  rerunSelectAllState,
  updateRerunSelection,
} from './case-rerun-selection';

const props = defineProps<{
  cases: PipelineRerunCandidateRecord[];
  runJobId: string;
}>();

const emit = defineEmits<{
  close: [];
  created: [runJob: PipelineRunJobRecord];
}>();

const submitting = ref(false);
const suiteSearch = ref('');
const caseSearch = ref('');
const statusFilter = ref('all');
const environmentFilter = ref('all');
const selectedCaseIds = ref(defaultRerunCaseIds(props.cases));

const suites = computed(() => {
  const keyword = suiteSearch.value.trim().toLowerCase();
  const names = new Set(
    props.cases
      .map((item) => item.suite_name)
      .filter((value): value is string => value !== null),
  );
  return [...names]
    .filter((name) => !keyword || name.toLowerCase().includes(keyword))
    .toSorted();
});

const selectedSuite = ref(suites.value[0] ?? '');
const activeSuite = computed(() =>
  suites.value.includes(selectedSuite.value)
    ? selectedSuite.value
    : (suites.value[0] ?? ''),
);

const environments = computed(() => {
  const items = new Map<string, string>();
  for (const item of props.cases) {
    if (!item.env_set_id) continue;
    const type = item.env_type === 'physical' ? '物理机' : 'VM';
    items.set(item.env_set_id, `环境套 ${item.env_set_index ?? '-'} · ${type}`);
  }
  return [...items.entries()];
});

const visibleCases = computed(() => {
  const keyword = caseSearch.value.trim().toLowerCase();
  return props.cases.filter((item) => {
    if (item.suite_name !== activeSuite.value) return false;
    if (statusFilter.value !== 'all' && item.status !== statusFilter.value) {
      return false;
    }
    if (
      environmentFilter.value !== 'all' &&
      item.env_set_id !== environmentFilter.value
    ) {
      return false;
    }
    return !keyword || (item.case_name ?? '').toLowerCase().includes(keyword);
  });
});

const submitCaseIds = computed(() => {
  const available = new Set(
    props.cases.filter((item) => item.can_rerun).map((item) => item.id),
  );
  return selectedCaseIds.value.filter((id) => available.has(id));
});
const selectedCount = computed(() => submitCaseIds.value.length);
const visibleSelectableIds = computed(() =>
  visibleCases.value.filter((item) => item.can_rerun).map((item) => item.id),
);
const selectAllState = computed(() =>
  rerunSelectAllState(selectedCaseIds.value, visibleCases.value),
);
const failedDefaultCount = computed(
  () =>
    props.cases.filter((item) => item.status === 'failed' && item.can_rerun)
      .length,
);

function statusLabel(status: string) {
  return (
    {
      error: '异常',
      failed: '失败',
      no_case: '无用例',
      not_executed: '未执行',
      passed: '通过',
      skipped: '跳过',
      timeout: '超时',
    }[status] ?? status
  );
}

function statusColor(status: string) {
  return { error: 'orange', failed: 'red', passed: 'green', timeout: 'gold' }[
    status
  ];
}

function suiteCases(suite: string) {
  return props.cases.filter((item) => item.suite_name === suite);
}

function suiteSelectableCases(suite: string) {
  return suiteCases(suite).filter((item) => item.can_rerun);
}

function suiteSelectedCount(suite: string) {
  return suiteCases(suite).filter((item) =>
    selectedCaseIds.value.includes(item.id),
  ).length;
}

function setSuiteSelection(suite: string, checked: boolean) {
  selectedCaseIds.value = updateRerunSelection(
    selectedCaseIds.value,
    suiteSelectableCases(suite).map((item) => item.id),
    checked,
  );
}

function setCaseSelection(caseRunId: string, checked: boolean) {
  selectedCaseIds.value = updateRerunSelection(
    selectedCaseIds.value,
    [caseRunId],
    checked,
  );
}

function setAllVisibleSelection(checked: boolean) {
  selectedCaseIds.value = updateRerunSelection(
    selectedCaseIds.value,
    visibleSelectableIds.value,
    checked,
  );
}

function resetFailedSelection() {
  selectedCaseIds.value = defaultRerunCaseIds(props.cases);
}

async function submit() {
  if (selectedCaseIds.value.length === 0) return;
  submitting.value = true;
  try {
    const runJob = await rerunRunJobCasesApi(
      props.runJobId,
      submitCaseIds.value,
    );
    message.success('用例重跑已创建');
    emit('created', runJob);
  } catch {
    message.error('环境状态已变化，请刷新后重试');
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <Modal
    :confirm-loading="submitting"
    :ok-button-props="{ disabled: selectedCount === 0 }"
    :ok-text="`重跑 ${selectedCount} 个用例`"
    :open="true"
    title="用例重跑"
    width="1100px"
    @cancel="emit('close')"
    @ok="submit"
  >
    <Alert
      class="mb-4"
      message="将在来源 VM 或物理机中执行，跳过完整环境准备；Docker 模块会重启 Docker。"
      show-icon
      type="info"
    />

    <div class="rerun-summary">
      <div>
        <span class="rerun-summary__count">{{ selectedCount }}</span>
        <span class="rerun-summary__label">已选用例</span>
        <span class="rerun-summary__default">
          默认失败项 {{ failedDefaultCount }} 个
        </span>
      </div>
      <div class="flex gap-2">
        <Button size="small" @click="resetFailedSelection">
          恢复默认失败项
        </Button>
        <Button size="small" @click="selectedCaseIds = []">清空</Button>
      </div>
    </div>

    <div class="rerun-picker">
      <aside class="rerun-suites">
        <Input
          v-model:value="suiteSearch"
          allow-clear
          placeholder="搜索 Suite"
        />
        <div class="rerun-suites__list">
          <button
            v-for="suite in suites"
            :key="suite"
            class="rerun-suite"
            :class="{ 'rerun-suite--active': activeSuite === suite }"
            type="button"
            @click="selectedSuite = suite"
          >
            <Checkbox
              :checked="
                suiteSelectableCases(suite).length > 0 &&
                suiteSelectedCount(suite) === suiteSelectableCases(suite).length
              "
              :indeterminate="
                suiteSelectedCount(suite) > 0 &&
                suiteSelectedCount(suite) < suiteSelectableCases(suite).length
              "
              @click.stop
              @update:checked="setSuiteSelection(suite, $event)"
            />
            <span class="rerun-suite__name">{{ suite }}</span>
            <span class="rerun-suite__count">
              {{ suiteSelectedCount(suite) }}/{{ suiteCases(suite).length }}
            </span>
          </button>
        </div>
      </aside>

      <section class="rerun-cases">
        <div class="rerun-cases__toolbar">
          <Input
            v-model:value="caseSearch"
            allow-clear
            placeholder="搜索 Case"
          />
          <Select v-model:value="statusFilter" style="width: 132px">
            <SelectOption value="all">全部状态</SelectOption>
            <SelectOption value="failed">失败</SelectOption>
            <SelectOption value="passed">通过</SelectOption>
            <SelectOption value="error">异常</SelectOption>
            <SelectOption value="timeout">超时</SelectOption>
            <SelectOption value="skipped">跳过</SelectOption>
            <SelectOption value="no_case">无用例</SelectOption>
            <SelectOption value="not_executed">未执行</SelectOption>
          </Select>
          <Select v-model:value="environmentFilter" style="width: 180px">
            <SelectOption value="all">全部环境</SelectOption>
            <SelectOption
              v-for="[id, label] in environments"
              :key="id"
              :value="id"
            >
              {{ label }}
            </SelectOption>
          </Select>
          <Checkbox
            :checked="selectAllState.checked"
            :disabled="visibleSelectableIds.length === 0"
            :indeterminate="selectAllState.indeterminate"
            @update:checked="setAllVisibleSelection"
          >
            全选
          </Checkbox>
        </div>
        <div class="rerun-cases__list">
          <div v-if="visibleCases.length === 0" class="rerun-empty">
            当前筛选下没有用例
          </div>
          <Tooltip
            v-for="caseRun in visibleCases"
            :key="caseRun.id"
            :title="caseRun.rerun_unavailable_reason ?? undefined"
          >
            <label
              class="rerun-case"
              :class="{ 'rerun-case--disabled': !caseRun.can_rerun }"
            >
              <Checkbox
                :checked="
                  caseRun.can_rerun && selectedCaseIds.includes(caseRun.id)
                "
                :disabled="!caseRun.can_rerun"
                @update:checked="setCaseSelection(caseRun.id, $event)"
              />
              <Tag :color="statusColor(caseRun.status)">
                {{ statusLabel(caseRun.status) }}
              </Tag>
              <span class="rerun-case__name">{{ caseRun.case_name }}</span>
              <span class="rerun-case__attempt">
                最近：{{
                  caseRun.latest_rerun_attempt === 0
                    ? '首次执行'
                    : `重跑 ${caseRun.latest_rerun_attempt}`
                }}
              </span>
              <Tag class="m-0" color="blue">
                环境套 {{ caseRun.env_set_index ?? '-' }}
              </Tag>
              <span class="rerun-case__env">
                {{ caseRun.env_type === 'physical' ? '物理机' : 'VM' }}
              </span>
            </label>
          </Tooltip>
        </div>
      </section>
    </div>
  </Modal>
</template>

<style scoped>
.rerun-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  margin-bottom: 12px;
  background: hsl(var(--muted) / 45%);
  border: 1px solid hsl(var(--border));
  border-radius: 6px;
}

.rerun-summary__count {
  margin-right: 6px;
  font-size: 22px;
  font-weight: 650;
  color: hsl(var(--primary));
}

.rerun-summary__label {
  font-weight: 500;
}

.rerun-summary__default {
  margin-left: 12px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.rerun-picker {
  display: grid;
  grid-template-columns: minmax(220px, 0.8fr) minmax(0, 2.2fr);
  min-height: 440px;
  overflow: hidden;
  border: 1px solid hsl(var(--border));
  border-radius: 8px;
}

.rerun-suites,
.rerun-cases {
  padding: 12px;
}

.rerun-suites {
  background: hsl(var(--muted) / 30%);
  border-right: 1px solid hsl(var(--border));
}

.rerun-suites__list,
.rerun-cases__list {
  max-height: 390px;
  margin-top: 10px;
  overflow: auto;
}

.rerun-suite {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  width: 100%;
  padding: 9px 10px;
  color: inherit;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: 6px;
}

.rerun-suite:hover,
.rerun-suite:focus-visible {
  outline: none;
  background: hsl(var(--accent));
}

.rerun-suite--active {
  background: hsl(var(--primary) / 9%);
  box-shadow: inset 3px 0 hsl(var(--primary));
}

.rerun-suite__name,
.rerun-case__name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rerun-suite__count,
.rerun-case__attempt,
.rerun-case__env {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.rerun-cases__toolbar {
  display: grid;
  grid-template-columns: 1fr auto auto auto;
  gap: 10px;
  align-items: center;
}

.rerun-case {
  display: grid;
  grid-template-columns: auto auto minmax(0, 1fr) auto auto auto;
  gap: 8px;
  align-items: center;
  padding: 10px 8px;
  border-bottom: 1px solid hsl(var(--border));
}

.rerun-case:hover {
  background: hsl(var(--accent) / 55%);
}

.rerun-case--disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.rerun-empty {
  padding: 64px 12px;
  color: hsl(var(--muted-foreground));
  text-align: center;
}

@media (max-width: 760px) {
  .rerun-summary {
    align-items: flex-start;
  }

  .rerun-summary__default {
    display: block;
    margin-left: 0;
  }

  .rerun-picker {
    grid-template-columns: 1fr;
  }

  .rerun-suites {
    border-right: 0;
    border-bottom: 1px solid hsl(var(--border));
  }

  .rerun-suites__list {
    max-height: 160px;
  }
}
</style>
