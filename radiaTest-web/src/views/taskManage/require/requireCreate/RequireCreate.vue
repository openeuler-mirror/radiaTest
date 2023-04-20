<template>
  <n-form
    ref="formRef"
    :label-width="80"
    :model="formValue"
    :rules="rules"
    size="medium"
    @valid="() => createModalRef.submitCreateForm()"
  >
    <n-grid :cols="24" :x-gap="20" :y-gap="10">
      <n-form-item-gi :span="24" label="标题" path="title">
        <n-input 
          v-model:value="formValue.title"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="16" label="简介" path="remark">
        <n-input 
          v-model:value="formValue.remark"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="8" label="发起方" path="publisher">
        <n-cascader
          v-model:value="formValue.publisher_group_id"
          placeholder="请选择需求发起方"
          :options="typeOptions"
          check-strategy="child"
          remote
          :on-load="handleLoad"
          @update:value="handlePublisherUpdate"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="16" label="里程碑" path="milestones">
        <n-select
          remote
          multiple
          filterable
          clearable
          v-model:value="formValue.milestones"
          :options="milestoneOptions"
          :loading="loading"
          @search="handleMilestoneSearch"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="4" label="预计工作量" path="payload">
        <n-input-number
          v-model:value="formValue.payload"
          :step="0.1"
          :min="0"
        >
          <template #suffix>
            人月
          </template>
        </n-input-number>
      </n-form-item-gi>
      <n-form-item-gi :span="4" label="交付周期" path="period">
        <n-input-number
          v-model:value="formValue.period"
          :min="0"
        >
          <template #suffix>
            天
          </template>
        </n-input-number>
      </n-form-item-gi>
      <n-form-item-gi :span="8" label="影响力奖励" path="total_reward">
        <n-input-number
          placeholder="消耗团队/个人影响力以设置需求奖励"
          style="width: 100%;"
          v-model:value="formValue.total_reward"
          :min="0"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="8" label="影响力门槛" path="influence_require">
        <n-input-number
          placeholder="接受方最低影响力要求"
          style="width: 100%;"
          v-model:value="formValue.influence_require"
          :min="0"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="8" label="信誉分门槛" path="behavior_require">
        <n-input-number 
          placeholder="接受方最低信誉分要求"
          style="width: 100%;"
          v-model:value="formValue.behavior_require"
          :min="0"
          :max="100"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="24" label="涉及软件包" path="packages">
        <n-dynamic-input v-model:value="formValue.packages" :on-create="onPackageCreate">
          <template #create-button-default>
            新增
          </template>
          <template #default="{ value }">
            <div style="display: flex; align-items: center; width: 100%">
              <n-input
                v-model:value="value.name"
                style="margin-right: 20px; width: 40%"
              />
              <n-checkbox-group v-model:value="value.targets">
                <n-space item-style="display: flex;">
                  <n-checkbox value="测试设计" label="测试设计" />
                  <n-checkbox value="用例开发" label="用例开发" />
                  <n-checkbox value="已执行" label="测试执行" />
                  <n-checkbox value="问题分析" label="问题分析" />
                </n-space>
              </n-checkbox-group>
            </div>
          </template>
        </n-dynamic-input>
      </n-form-item-gi>
      <n-form-item-gi :span="24" label="需求详述" path="description">
        <n-input
          type="textarea"
          placeholder="为接受者提供充分的需求描述"
          v-model:value="formValue.description"
          :autosize="{
            minRows: 10,
            maxRows: 50,
          }"
        />
      </n-form-item-gi>
    </n-grid>
  </n-form>
</template>

<script setup>
import { useMessage } from 'naive-ui';
import { getGroup, getAllMilestone } from '@/api/get';
import { orgPublishRequire, groupPublishRequire, publishRequire } from '@/api/post';
import { storage } from '@/assets/utils/storageUtils';

const emit = defineEmits(['valid']);

const message = useMessage();

const loading = ref(false);
const milestoneOptions = ref([]);
const formRef = ref(null);
const formValue = ref({
  title: null,
  remark: null,
  description: null,
  publisher_type: 'person',
  publisher_group_id: null,
  publisher_group_name: null,
  payload: 0,
  period: 0,
  milestones: [],
  packages: [],
  behavior_require: 0,
  influence_require: 0,
  total_reward: 0,
});

const rules = {
  title: {
    trigger: ['blur', 'change'],
    required: true,
    message: '需求标题不可为空',
  },
  remark: {
    trigger: ['blur', 'change'],
    required: true,
    message: '需求简介不可为空',
  },
  description: {
    trigger: ['blur', 'change'],
    required: true,
    message: '需求详情不可为空',
  },
  milestones: {
    trigger: ['blur', 'change'],
    required: true,
    validator () {
      if (formValue.value.milestones.length === 0) {
        return Error('至少需要关联一个里程碑');
      }
      return true;
    }
  }
};

const typeOptions = ref([
  { label: '组织', value: 'organization', isLeaf: true },
  { label: '团队', value: 'group', isLeaf: false },
  { label: '个人', value: 'person', isLeaf: true }
]);
function handleLoad(option) {
  return new Promise((resolve, reject) => {
    getGroup({ page_num: 1, page_size: 99999 })
      .then((res) => {
        option.children = res.data.items.map((item) => ({
          label: item.name,
          value: item.id,
        }));
        resolve();
      })
      .catch((err) => reject(err));
  });
}
function handlePublisherUpdate(value, option) {
  if (typeof(value) === 'number') {
    formValue.value.publisher_type = 'group';
    formValue.value.publisher_group_name = option.label;
  } else {
    formValue.value.publisher_type = value;
    formValue.value.publisher_group_id = option.label;
    formValue.value.publisher_group_name = null;
  }
}

function handleMilestoneSearch(query) {
  loading.value = true;
  getAllMilestone({ name: query, paged: false })
    .then((res) => {
      const milestoneList = res.data?.items || [];
      milestoneOptions.value = milestoneList.map((item) => {
        return {
          label: item.name,
          value: item.id,
        };
      });
    })
    .finally(() => {
      loading.value = false;
    });
}

function onPackageCreate() {
  return {
    name: '',
    targets: [],
  };
}

function handlePropsButtonClick() {
  formRef.value.validate((error) => {
    if (error) {
      message.error('请重新填写相关信息');
    } else if (formValue.value.publisher_type === 'organization') {
      const _form = JSON.parse(JSON.stringify(formValue.value));
      _form.publisher_group_id = null;
      orgPublishRequire(storage.getValue('loginOrgId'), _form)
        .then(() => {
          message.success('需求已成功发布');
          emit('valid');
        });
    } else if (formValue.value.publisher_type === 'group') {
      const _form = JSON.parse(JSON.stringify(formValue.value));
      groupPublishRequire(_form.publisher_group_id, _form)
        .then(() => {
          message.success('需求已成功发布');
          emit('valid');
        });
    } else {
      const _form = JSON.parse(JSON.stringify(formValue.value));
      publishRequire(_form)
        .then(() => {
          message.success('需求已成功发布');
          emit('valid');
        });
    }
  });
}

onMounted(() => {
  handleMilestoneSearch('');
});

defineExpose({ handlePropsButtonClick });
</script>

<style scoped lang="less">
.package-item {
  display: flex;
  margin: 10px 0 10px 0;
}
</style>
