<template>
  <n-card style="min-width: 680px; max-width: 1280px">
    <n-card
      id="baseinfoCard"
      :title="createTitle('填写模板基础信息')"
      size="huge"
      :bordered="false"
      :segmented="{
        content: 'hard'
      }"
      header-style="
            font-size: 20px; 
            height: 40px;
            padding-top: 10px;
            padding-bottom: 10px; 
            font-family: 'v-sans'; 
            background-color: rgba(250,250,252,1);
        "
    >
      <div>
        <n-form inline :label-width="80" :model="formValue" :rules="rules" size="medium" ref="formRef">
          <n-grid :cols="24" :x-gap="36">
            <n-form-item-gi :span="10" label="模板名" path="name">
              <n-input v-model:value="formValue.name" style="width: 90%" placeholder="模版名称不可与已有模板重复" />
            </n-form-item-gi>
            <n-form-item-gi :span="6" label="类型" path="permission_type">
              <n-cascader
                v-model:value="formValue.permission_type"
                placeholder="请选择"
                :options="typeOptions"
                check-strategy="child"
                remote
                :disabled="isEditTemplate"
                :on-load="handleLoad"
              />
            </n-form-item-gi>
            <n-form-item-gi :span="6" label="产品" path="product">
              <n-select :options="productOpts" v-model:value="formValue.product" placeholder="选择产品" filterable />
            </n-form-item-gi>
            <n-gi :span="8">
              <n-form-item label="版本" path="version">
                <n-select :options="versionOpts" v-model:value="formValue.version" placeholder="选择版本" filterable />
              </n-form-item>
            </n-gi>
            <n-form-item-gi :span="16" label="里程碑" path="milestone_id">
              <n-select
                :options="milestoneOpts"
                v-model:value="formValue.milestone_id"
                placeholder="选择模板绑定的里程碑"
                filterable
              />
            </n-form-item-gi>
            <n-form-item-gi :span="8" label="测试脚本代码仓" path="git_repo_id">
              <n-select
                :options="gitRepoOpts"
                v-model:value="formValue.git_repo_id"
                placeholder="选择模板绑定的测试脚本代码仓"
                filterable
              />
            </n-form-item-gi>
            <n-form-item-gi :span="16" label="模板描述" path="description">
              <n-input v-model:value="formValue.description" />
            </n-form-item-gi>
            <n-form-item-gi :span="24" label="绑定测试用例" path="file">
              <n-upload
                v-model:file-list="formValue.file"
                :max="1"
                :default-upload="false"
                accept=".json,.xls,.xlsx"
                :trigger-style="{ width: '84px' }"
              >
                <n-button>上传文件</n-button>
              </n-upload>
            </n-form-item-gi>
          </n-grid>
        </n-form>
      </div>
    </n-card>
    <n-space class="NPbutton">
      <n-button size="large" type="error" @click="onNegativeClick" ghost>取消 </n-button>
      <n-button size="large" type="primary" @click="onPositiveClick" ghost> 提交 </n-button>
    </n-space>
  </n-card>
</template>

<script setup>
import { createTitle } from '@/assets/utils/createTitle';
import createAjax from '@/views/testCenter/template/modules/createAjax.js';
import extendForm from '@/views/versionManagement/product/modules/createForm.js';
import { getProductOpts, getVersionOpts, getMilestoneOpts } from '@/assets/utils/getOpts.js';
import { createRepoOptions } from '@/assets/utils/getOpts';
import { updateTemplateDrawer } from '@/api/put.js';

const emit = defineEmits(['onNegativeClick']);
const props = defineProps(['modalData', 'isEditTemplate']);
const { modalData, isEditTemplate } = toRefs(props);

const formRef = ref(null);
const formValue = ref({
  name: undefined,
  product: undefined,
  version: undefined,
  milestone_id: undefined,
  description: undefined,
  git_repo_id: undefined,
  permission_type: undefined,
  file: undefined
});
const rules = {
  name: {
    required: true,
    message: '模板名不可为空',
    trigger: ['blur']
  },
  formwork_type: {
    required: true,
    message: '模板类型不可为空',
    trigger: ['blur']
  },
  milestone_id: {
    required: true,
    message: '请绑定里程碑',
    trigger: ['blur']
  },
  permission_type: {
    required: true,
    message: '请选择类型',
    trigger: ['blur']
  },
  product: {
    required: true,
    message: '请选择产品',
    trigger: ['blur']
  },
  version: {
    required: true,
    message: '请选择版本',
    trigger: ['blur']
  },
  git_repo_id: {
    required: true,
    message: '请选择代码仓',
    trigger: ['blur']
  },
  file: {
    required: true,
    message: '请上传测试用例',
    validator(rule, value) {
      if (value?.length) {
        return true;
      }
      return false;
    }
  }
};

const clean = () => {
  formValue.value = {
    name: undefined,
    product: undefined,
    version: undefined,
    milestone_id: undefined,
    description: undefined,
    git_repo_id: undefined,
    permission_type: undefined,
    file: undefined
  };
};

// 类型
const typeOptions = ref([
  { label: '组织', value: 'org', isLeaf: true },
  { label: '团队', value: 'group', isLeaf: false },
  { label: '个人', value: 'person', isLeaf: true }
]);
const handleLoad = extendForm.handleLoad;

const productOpts = ref([]); // 产品
const gitRepoOpts = ref(); // 代码仓
const getProductOptions = async () => {
  getProductOpts(productOpts);
  gitRepoOpts.value = await createRepoOptions();
};

const versionOpts = ref([]);
watch(
  () => formValue.value.product,
  () => {
    getVersionOpts(versionOpts, formValue.value.product);
  }
);

const milestoneOpts = ref([]);
watch(
  () => formValue.value.version,
  () => {
    getMilestoneOpts(milestoneOpts, formValue.value.version);
  }
);

const onPositiveClick = () => {
  formRef.value.validate(async (error) => {
    if (error) {
      window.$message?.error('请检查输入合法性');
    } else {
      if (isEditTemplate.value) {
        const formData = new FormData();
        formData.append('name', formValue.value.name);
        formData.append('milestone_id', formValue.value.milestone_id);
        formData.append('description', formValue.value.description);
        formData.append('git_repo_id', formValue.value.git_repo_id);
        formData.append('file', formValue.value.file[0]?.file);
        await updateTemplateDrawer(formData, modalData.value.id);
      } else {
        await createAjax.postForm(formValue);
      }
      emit('onNegativeClick');
    }
  });
};

const onNegativeClick = () => {
  emit('onNegativeClick');
};

onMounted(() => {
  getProductOptions();
  if (isEditTemplate.value) {
    formValue.value.name = modalData.value.name;
    formValue.value.permission_type = modalData.value.template_type;
    formValue.value.description = modalData.value.description;
    formValue.value.git_repo_id = String(modalData.value.git_repo.id);
  }
});

onUnmounted(() => {
  clean();
});
</script>

<style scoped></style>
