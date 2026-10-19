<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import type {
  KernelVariantRecord,
  MugenCaseRecord,
  PipelineConfigRecord,
  VMImageRecord,
} from '#/api';

import { computed, onMounted, reactive, ref, watch } from 'vue';

import {
  Button,
  Checkbox,
  Collapse,
  CollapsePanel,
  Empty,
  Input,
  Select,
  Switch,
  Tag,
} from 'ant-design-vue';

import {
  getAllTestCasesApi,
  getKernelVariantsApi,
  getVMImagesApi,
} from '#/api';

import { groupCasesBySuite } from '../test-jobs/test-job-view';
import { buildReleaseCaseSelections } from './release-config-view';

const props = defineProps<{
  config: null | PipelineConfigRecord;
}>();

const images = ref<VMImageRecord[]>([]);
const cases = ref<MugenCaseRecord[]>([]);
const kernelVariants = ref<KernelVariantRecord[]>([]);
const variantsLoading = ref(false);
const suiteFilter = ref('');
// 已选 case：suite → 选中 case 名集合（显式）。suite 存在 key 即已选入。
const selectedCases = reactive<Record<string, string[]>>({});
// 右侧展开的 suite（精细筛选用）——选 suite 不自动展开，手动点下拉才展
const expandedSuites = ref<string[]>([]);
// hydrating 守卫：resetForm 填值时跳过级联 watcher，避免把刚填的下游字段清空
const hydrating = ref(false);

const form = reactive({
  archs: [] as string[],
  dist: 'openEuler',
  imageRound: '',
  kernelRpmUrl: '',
  kernelVariant: '',
  osVersion: '',
  physicalEnabled: false,
});

const groupedCases = computed(() => groupCasesBySuite(cases.value));
const suites = computed(() => [...groupedCases.value.keys()]);
const filteredSuites = computed(() => {
  const kw = suiteFilter.value.trim().toLowerCase();
  return kw
    ? suites.value.filter((s) => s.toLowerCase().includes(kw))
    : suites.value;
});

const distOptions = computed(() => {
  const set = new Set(images.value.map((i) => i.dist));
  return [...set].map((v) => ({ label: v, value: v }));
});
const osVersionOptions = computed(() => {
  const set = new Set(
    images.value.filter((i) => i.dist === form.dist).map((i) => i.os_version),
  );
  return [...set].map((v) => ({ label: v, value: v }));
});
const roundOptions = computed(() => {
  const set = new Set(
    images.value
      .filter((i) => i.dist === form.dist && i.os_version === form.osVersion)
      .map((i) => i.image_round),
  );
  return [...set].map((v) => ({ label: v, value: v }));
});
const archOptions = computed(() => {
  const set = new Set(
    images.value
      .filter(
        (i) =>
          i.dist === form.dist &&
          i.os_version === form.osVersion &&
          i.image_round === form.imageRound,
      )
      .map((i) => i.arch),
  );
  return [...set];
});

const selectedSuites = computed(() => Object.keys(selectedCases));
const totalSelectedCases = computed(() =>
  selectedSuites.value.reduce(
    (sum, s) => sum + (selectedCases[s]?.length ?? 0),
    0,
  ),
);

function suiteCaseNames(suite: string): string[] {
  return (groupedCases.value.get(suite) ?? []).map((c) => c.case_name);
}

function isSuiteSelected(suite: string): boolean {
  return suite in selectedCases;
}

function toggleSuite(suite: string, checked: boolean) {
  if (checked) {
    // 选中 suite → 默认全选 case（显式全集）；不自动展开，用户手动下拉看 case
    selectedCases[suite] = [...suiteCaseNames(suite)];
  } else {
    delete selectedCases[suite];
  }
}

function caseChecked(suite: string, caseName: string): boolean {
  return selectedCases[suite]?.includes(caseName) ?? false;
}

function toggleCase(suite: string, caseName: string, checked: boolean) {
  const set = new Set(selectedCases[suite]);
  if (checked) set.add(caseName);
  else set.delete(caseName);
  selectedCases[suite] = [...set];
}

function removeSuite(suite: string) {
  delete selectedCases[suite];
}

/** 全选用例：所有 suite 的全部 case 显式选入（物理机用例执行时自动跳过为 NOT_EXECUTED）。 */
function selectAllCases() {
  for (const suite of suites.value) {
    selectedCases[suite] = suiteCaseNames(suite);
  }
}

// 内核变体与 RPM URL 互斥：设其一则清另一（watch 驱动）
watch(
  () => form.kernelVariant,
  (v) => {
    if (v) form.kernelRpmUrl = '';
  },
);
watch(
  () => form.kernelRpmUrl,
  (v) => {
    if (v) form.kernelVariant = '';
  },
);

async function loadImages() {
  try {
    images.value = await getVMImagesApi();
  } catch {
    images.value = [];
  }
}

async function loadCases() {
  try {
    cases.value = await getAllTestCasesApi({ env_type: 'vm' });
  } catch {
    cases.value = [];
  }
}

async function loadKernelVariants() {
  if (!form.osVersion || !form.imageRound || form.archs.length === 0) {
    kernelVariants.value = [];
    return;
  }
  variantsLoading.value = true;
  try {
    const perArch = await Promise.all(
      form.archs.map((arch) =>
        getKernelVariantsApi({
          arch,
          image_round: form.imageRound,
          os_version: form.osVersion,
        }).catch(() => [] as KernelVariantRecord[]),
      ),
    );
    const sets = perArch.map((list) => new Set(list.map((v) => v.variant)));
    const first = perArch[0];
    if (!first || first.length === 0) {
      kernelVariants.value = [];
      return;
    }
    kernelVariants.value = first.filter((v) =>
      sets.every((s) => s.has(v.variant)),
    );
  } finally {
    variantsLoading.value = false;
  }
}

function resetForm() {
  hydrating.value = true;
  try {
    form.dist = 'openEuler';
    form.osVersion = '';
    form.imageRound = '';
    form.archs = [];
    form.kernelVariant = '';
    form.kernelRpmUrl = '';
    form.physicalEnabled = false;
    suiteFilter.value = '';
    for (const key of Object.keys(selectedCases)) delete selectedCases[key];
    expandedSuites.value = [];
    const config = props.config;
    if (config) {
      form.dist = config.dist ?? 'openEuler';
      form.osVersion = config.versions[0] ?? '';
      form.imageRound = config.image_round ?? '';
      form.archs = [...config.archs];
      form.kernelVariant =
        (config.config_data?.kernel_variant as string | undefined) ?? '';
      form.kernelRpmUrl =
        (config.config_data?.kernel_rpm_url as string | undefined) ?? '';
      form.physicalEnabled =
        (config.config_data?.release_physical_enabled as boolean | undefined) ??
        false;
      const sels =
        (config.config_data?.case_selections as
          | undefined
          | { case_names?: string[]; suite_name: string }[]) ?? [];
      for (const sel of sels) {
        const all = suiteCaseNames(sel.suite_name);
        if (all.length === 0) continue;
        const named = sel.case_names ?? [];
        selectedCases[sel.suite_name] =
          named.length === 0 ? [...all] : all.filter((c) => named.includes(c));
      }
      // 编辑时不预展开，让用户自行下拉
    }
  } finally {
    hydrating.value = false;
  }
  // 编辑时 archs-watcher 被 hydrating 跳过，手动加载内核变体选项（让 Select 显示已存值）
  if (props.config && form.archs.length > 0) {
    void loadKernelVariants();
  }
}

/** 供父弹窗提交时调用：返回除 name/pipeline_type 外的 payload。 */
function getData() {
  const configData: Record<string, unknown> = {
    case_selections: buildReleaseCaseSelections(
      { ...selectedCases },
      cases.value,
    ),
    release_physical_enabled: form.physicalEnabled,
  };
  if (form.kernelVariant) configData.kernel_variant = form.kernelVariant;
  if (form.kernelRpmUrl) configData.kernel_rpm_url = form.kernelRpmUrl;
  return {
    archs: form.archs,
    config_data: configData,
    dist: form.dist,
    image_round: form.imageRound,
    versions: [form.osVersion],
  };
}

/** 供父弹窗提交前校验：返回错误信息或 null。 */
function validate(): null | string {
  if (!form.osVersion) return '请选择 OS 版本';
  if (!form.imageRound) return '请选择轮次';
  if (form.archs.length === 0) return '请至少选择一个架构';
  if (selectedSuites.value.length === 0) return '请至少选择一个 Suite';
  return null;
}

async function ensureLoaded() {
  if (images.value.length === 0) await loadImages();
  if (cases.value.length === 0) await loadCases();
}

defineExpose({ resetForm, getData, validate, ensureLoaded });

onMounted(async () => {
  await ensureLoaded();
  resetForm();
});

watch(
  () => form.dist,
  () => {
    if (hydrating.value) return;
    form.osVersion = '';
    form.imageRound = '';
    form.archs = [];
  },
);
watch(
  () => form.osVersion,
  () => {
    if (hydrating.value) return;
    form.imageRound = '';
    form.archs = [];
  },
);
watch(
  () => form.imageRound,
  () => {
    if (hydrating.value) return;
    form.archs = [];
  },
);
watch(
  () => form.archs,
  () => {
    if (hydrating.value) return;
    form.kernelVariant = '';
    loadKernelVariants();
  },
  { deep: true },
);
</script>

<template>
  <div class="space-y-4">
    <div class="release-form-grid">
      <div>
        <span class="release-label">发行版</span>
        <Select
          v-model:value="form.dist"
          :options="distOptions"
          class="w-full"
        />
      </div>
      <div>
        <span class="release-label release-label--required">OS 版本</span>
        <Select
          v-model:value="form.osVersion"
          :options="osVersionOptions"
          class="w-full"
          placeholder="选择 OS 版本"
        />
      </div>
      <div>
        <span class="release-label release-label--required">轮次</span>
        <Select
          v-model:value="form.imageRound"
          :options="roundOptions"
          class="w-full"
          placeholder="选择镜像轮次"
        />
      </div>
      <div>
        <span class="release-label release-label--required">架构</span>
        <Checkbox.Group v-model:value="form.archs">
          <Checkbox v-for="arch in archOptions" :key="arch" :value="arch">
            {{ arch }}
          </Checkbox>
        </Checkbox.Group>
      </div>
      <div>
        <span class="release-label">内核变体</span>
        <Select
          v-model:value="form.kernelVariant"
          :options="
            kernelVariants.map((v) => ({
              label: `${v.kernel_version_prefix} (${v.variant})`,
              value: v.variant,
            }))
          "
          :loading="variantsLoading"
          allow-clear
          class="w-full"
          placeholder="可选，跨架构交集"
        />
      </div>
      <div>
        <span class="release-label">内核 RPM URL（与变体互斥）</span>
        <Input
          v-model:value="form.kernelRpmUrl"
          allow-clear
          placeholder="http://.../kernel-*.rpm"
        />
      </div>
    </div>

    <div class="mb-3 flex items-center gap-3 border-t border-border pt-3">
      <span class="text-sm font-semibold">执行物理机用例</span>
      <Switch v-model:checked="form.physicalEnabled" size="small" />
      <span class="text-xs text-gray-400">
        开启后为物理机用例租用物理机执行；关闭时跳过（标记为未执行），不影响虚拟机用例
      </span>
    </div>

    <section class="space-y-2 border-t border-border pt-3">
      <div class="release-toolbar">
        <span class="text-sm font-semibold">选择 Suite / Case</span>
        <div class="flex gap-2">
          <Tag>{{ selectedSuites.length }} 个 Suite</Tag>
          <Tag color="blue">{{ totalSelectedCases }} 个 Case</Tag>
        </div>
      </div>
      <div class="release-picker">
        <div class="release-picker__pane">
          <Input
            v-model:value="suiteFilter"
            allow-clear
            placeholder="过滤 Suite"
          />
          <Button size="small" @click="selectAllCases">全选用例</Button>
          <div class="release-picker__list">
            <div
              v-for="suite in filteredSuites"
              :key="suite"
              class="release-picker__row"
              :class="{
                'release-picker__row--active': isSuiteSelected(suite),
              }"
              @click="toggleSuite(suite, !isSuiteSelected(suite))"
            >
              <Checkbox
                :checked="isSuiteSelected(suite)"
                @click.stop
                @update:checked="toggleSuite(suite, Boolean($event))"
              />
              <span class="min-w-0 flex-1 truncate">{{ suite }}</span>
              <span class="release-picker__count">
                {{ suiteCaseNames(suite).length }} case
              </span>
            </div>
            <Empty
              v-if="filteredSuites.length === 0"
              :image="Empty.PRESENTED_IMAGE_SIMPLE"
              description="无匹配 Suite"
            />
          </div>
        </div>
        <div class="release-picker__pane">
          <div class="release-picker__head">
            已选（点 Suite 下拉展开看 case，精细取消；x 移除整 Suite）
          </div>
          <div class="release-picker__list">
            <div
              v-if="selectedSuites.length === 0"
              class="release-picker__empty"
            >
              左侧选择 Suite 后在此展示，默认全选其 case（点下拉查看/取消）
            </div>
            <Collapse
              v-else
              v-model:active-key="expandedSuites"
              :bordered="false"
            >
              <CollapsePanel
                v-for="suite in selectedSuites"
                :key="suite"
                :header="`${suite} (${selectedCases[suite]?.length ?? 0}/${suiteCaseNames(suite).length})`"
              >
                <template #extra>
                  <Button
                    size="small"
                    type="link"
                    danger
                    @click.stop="removeSuite(suite)"
                  >
                    移除
                  </Button>
                </template>
                <div class="release-case-grid">
                  <label
                    v-for="c in groupedCases.get(suite) ?? []"
                    :key="c.case_name"
                    class="release-case-row"
                  >
                    <Checkbox
                      :checked="caseChecked(suite, c.case_name)"
                      @update:checked="
                        toggleCase(suite, c.case_name, Boolean($event))
                      "
                    />
                    <span class="min-w-0 flex-1 break-all">{{
                      c.case_name
                    }}</span>
                    <span class="release-picker__count">{{ c.node_num }}N</span>
                  </label>
                </div>
              </CollapsePanel>
            </Collapse>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.release-form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.release-label {
  display: block;
  margin-bottom: 4px;
  font-size: 13px;
  color: hsl(var(--muted-foreground));
}

.release-label--required::after {
  color: hsl(var(--destructive));
  content: ' *';
}

.release-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.release-picker {
  display: grid;
  grid-template-columns: minmax(280px, 0.7fr) minmax(400px, 1.3fr);
  gap: 12px;
}

.release-picker__pane {
  min-width: 0;
  padding: 12px;
  border: 1px solid hsl(var(--border));
}

.release-picker__head {
  margin-bottom: 8px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.release-picker__list {
  height: 340px;
  margin-top: 8px;
  overflow: auto;
}

.release-picker__row {
  display: flex;
  gap: 8px;
  align-items: center;
  min-height: 34px;
  padding: 4px 8px;
  cursor: pointer;
}

.release-picker__row:hover,
.release-picker__row--active {
  background: hsl(var(--accent));
}

.release-picker__count {
  font-size: 11px;
  color: hsl(var(--muted-foreground));
}

.release-picker__empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: 13px;
  color: hsl(var(--muted-foreground));
}

.release-case-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 4px;
}

.release-case-row {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 3px 4px;
}

@media (max-width: 768px) {
  .release-form-grid,
  .release-picker {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
