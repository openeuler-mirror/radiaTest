<template>
  <n-card style="min-width: 680px; max-width: 1280px">
    <n-card
      id="baseinfoCard"
      :title="createTitle('填写模板基础信息')"
      size="huge"
      :bordered="false"
      :segmented="{
        content: 'hard',
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
        <n-form
          inline
          :label-width="80"
          :model="formValue"
          :rules="rules"
          size="medium"
          ref="formRef"
        >
          <n-grid :cols="24" :x-gap="36">
            <n-form-item-gi :span="10" label="模板名" path="name">
              <n-input
                v-model:value="formValue.name"
                style="width: 90%"
                placeholder="模版名称不可与已有模板重复"
              />
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
              <n-select
                :options="productOpts"
                v-model:value="formValue.product"
                placeholder="选择产品"
                filterable
              />
            </n-form-item-gi>
            <n-gi :span="8">
              <n-form-item label="版本" path="version">
                <n-select
                  :options="versionOpts"
                  v-model:value="formValue.version"
                  placeholder="选择版本"
                  filterable
                />
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
            <!-- <n-form-item-gi :span="8" label="测试脚本代码仓" path="git_repo_id">
              <n-select
                :options="gitRepoOpts"
                v-model:value="formValue.git_repo_id"
                placeholder="选择模板绑定的测试脚本代码仓"
                @update:value="changeRepo"
                filterable
              />
            </n-form-item-gi> -->
            <n-form-item-gi :span="16" label="模板描述" path="description">
              <n-input v-model:value="formValue.description" />
            </n-form-item-gi>
            <n-form-item-gi :span="24" label="绑定测试用例" path="file">
              <n-switch
                class="case-switch"
                v-model:value="isUploadCases"
                @update:value="changeRepo"
              >
                <template #checked> 上传 </template>
                <template #unchecked> 勾选 </template>
              </n-switch>
              <n-spin :show="showLoading" style="width: 100%">
                <n-upload
                  v-if="isUploadCases"
                  v-model:file-list="formValue.file"
                  :max="1"
                  :default-upload="false"
                  accept=".json,.xls,.xlsx"
                  :trigger-style="{ width: '84px' }"
                >
                  <n-button>上传文件</n-button>
                </n-upload>
                <n-transfer
                  class="modalTransfer"
                  v-else
                  ref="transfer"
                  select-all-text=""
                  v-model:value="formValue.cases"
                  :options="flattenTree(casesOption)"
                  :render-source-list="renderSourceList"
                  target-filterable
                  virtual-scroll
                />
              </n-spin>
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
import { getCaseSuite, getCases } from '@/api/get.js';
import { NTree, NInput, NScrollbar } from 'naive-ui';
import _ from 'lodash';
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
  file: undefined,
  cases: [],
});
const rules = {
  name: {
    required: true,
    message: '模板名不可为空',
    trigger: ['blur'],
  },
  formwork_type: {
    required: true,
    message: '模板类型不可为空',
    trigger: ['blur'],
  },
  milestone_id: {
    required: true,
    message: '请绑定里程碑',
    trigger: ['blur'],
  },
  permission_type: {
    required: true,
    message: '请选择类型',
    trigger: ['blur'],
  },
  product: {
    required: true,
    message: '请选择产品',
    trigger: ['blur'],
  },
  version: {
    required: true,
    message: '请选择版本',
    trigger: ['blur'],
  },
  git_repo_id: {
    required: true,
    message: '请选择代码仓',
    trigger: ['blur'],
  },
  file: {
    required: true,
    message: '请上传或勾选测试用例',
    validator(rule, value) {
      if (isUploadCases.value) {
        if (value?.length) {
          return true;
        }
        return false;
      } else if (formValue.value.cases?.length) {
        return true;
      }
      return false;
    },
  },
};

const isUploadCases = ref(true);
const queryPageSize = 20;
const clean = () => {
  formValue.value = {
    name: undefined,
    product: undefined,
    version: undefined,
    milestone_id: undefined,
    description: undefined,
    git_repo_id: undefined,
    permission_type: undefined,
    file: undefined,
    cases: [],
  };
};

// 类型
const typeOptions = ref([
  { label: '组织', value: 'org', isLeaf: true },
  { label: '团队', value: 'group', isLeaf: false },
  { label: '个人', value: 'person', isLeaf: true },
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

const axiosStatus = ref(false);
const showLoading = computed(() => {
  return !isUploadCases.value && axiosStatus.value;
});
const flattenTree = (list) => {
  const result = [];
  function flatten(_list = []) {
    _list.forEach((item) => {
      result.push(item);
      flatten(item.children);
    });
  }
  flatten(list);
  return result;
};
// 上传文件用例或者选择用例
const changeRepo = (value) => {
  if (!value) {
    axiosStatus.value = true;
    formValue.value.cases = [];
    casesOption.value = [];
    suitePageNum.value = 1;
    getCaseOptions();
  }
};
// 获取树节点--父节点--测试套
const casesOption = ref([]);
const suitePageNum = ref(1);
const hasSuiteNext = ref(true);
const suiteIds = ref([]);
const getCaseOptions = () => {
  let param = {
    page_num: suitePageNum.value,
    page_size: 20,
  };
  getCaseSuite(param).then((res) => {
    axiosStatus.value = false;
    res.data.items.forEach((item) => {
      casesOption.value.push({
        label: item.name,
        key: `suite-${item.id}`,
        value: `suite-${item.id}`,
        isLeaf: false,
      });
      suiteIds.value.push(`suite-${item.id}`);
    });
    hasSuiteNext.value = res.data.has_next;
    if (res.data.has_next) {
      suitePageNum.value = res.data.next_num;
    }
  });
};

const tempSelectedKeys = ref([]);
const tempSelectedOptions = ref([]);
const renderSourceList = ({ onCheck }) => {
  return [
    h(NInput, {
      size: 'small',
      style: { margin: '5px 0 5px 10px', width: '552px' },
      placeholder: '请输入',
      onInput: handleFilter,
    }),
    h(
      NScrollbar,
      {
        style: 'max-height: 200px; margin-top:38px',
        onScroll: handleScrollBar,
      },
      [
        h(NTree, {
          keyField: 'value',
          checkable: true,
          selectable: false,
          blockLine: true,
          // checkOnClick: true,
          cascade: true,
          checkStrategy: 'child',
          showIrrelevantNodes: false,
          defaultExpandedKeys: defaultExpandKeys.value,
          data: casesOption.value,
          onLoad: handleTreeLoad,
          checkedKeys: formValue.value.cases,
          allowCheckingNotLoaded: true,
          expandOnClick: true,
          onUpdateCheckedKeys: async (checkedKeys, options) => {
            let newCheckedKeys = _.cloneDeep(checkedKeys);
            let newOptions = _.cloneDeep(options);
            // 当选择的是父亲节点（全选）时，先请求它的子节点，再将子节点替换掉已选中的父节点
            if (options.length) {
              let isLeaf = options[options.length - 1].isLeaf
                ? options[options.length - 1].isLeaf
                : null;
              if (!isLeaf) {
                formValue.value.cases = [];
                await getChildLeaf(10000, options[options.length - 1]);
                Array.prototype.splice.apply(
                  newCheckedKeys,
                  [-1, tempChildKeys.value.length].concat(tempChildKeys.value)
                );
                Array.prototype.splice.apply(
                  newOptions,
                  [-1, tempChildOptions.value.length].concat(tempChildOptions.value)
                );
              }
            }
            tempSelectedKeys.value = newCheckedKeys;
            tempSelectedOptions.value = newOptions;
            onCheck(newCheckedKeys);
          },
        }),
      ]
    ),
  ];
};
// 滚动异步加载
const handleScrollBar = (e) => {
  const currentTarget = e.currentTarget;
  if (currentTarget.scrollTop + currentTarget.offsetHeight >= currentTarget.scrollHeight) {
    if (!patternValue.value && hasSuiteNext.value) {
      getCaseOptions();
    } else if (hasChildNext.value) {
      getChildLeaf(queryPageSize);
    }
  }
};
// 异步加载树子节点
const handleTreeLoad = (node) => {
  return new Promise((resolve) => {
    let childPageSize = 10000;
    getChildLeaf(childPageSize, node, resolve);
  });
};
const hasChildNext = ref(true);
const tempChildKeys = ref([]);
const tempChildOptions = ref([]);
const getChildLeaf = async (pageSize, node, resolve) => {
  let params = {
    page_num: pageSize === 10000 ? 1 : childPageNum.value,
    page_size: pageSize,
    suite_id: node ? node.value.replace('suite-', '') : null,
    suite_name: node ? node.label : null,
    name: patternValue.value,
  };
  await getCases(params)
    .then((res) => {
      let leaf = [];
      let leafKey = [];
      let keyItem;
      res.data.items.length &&
        res.data.items.forEach((item) => {
          keyItem = {
            label: item.name,
            value: `case-${item.id}`,
            key: `case-${item.id}`,
            isLeaf: true,
            suiteId: `suite-${item.suite_id}`,
            suite: {
              label: item.suite,
              value: `suite-${item.suite_id}`,
              key: `suite-${item.suite_id}`,
              isLeaf: false,
            },
          };
          leaf.push(keyItem);
          leafArray.value.push(keyItem);
          leafKey.push(`case-${item.id}`);
        });
      tempChildKeys.value = leafKey;
      tempChildOptions.value = leaf;

      if (node) {
        // 点击树节点展开时候的叶子
        node.children = leaf;
        resolve && resolve();
      } else {
        //搜索的时候返回的叶子
        casesOption.value = leafArray.value;
        hasChildNext.value = res.data.has_next;
        if (res.data.has_next) {
          childPageNum.value = res.data.next_num;
        }
        // 搜索时候将之前选中的缓存中的数据加到目前有的数据中
        casesOption.value = casesOption.value.concat(tempSelectedOptions.value);
      }
    })
    .catch(() => {});
};

// 穿梭框异步查询
const patternValue = ref(null);
const childPageNum = ref(1);
const leafArray = ref([]);
const defaultExpandKeys = ref([]);
const handleFilter = async (pattern) => {
  //请求接口返回的树数据逻辑
  patternValue.value = pattern.trim();
  if (pattern.trim()) {
    leafArray.value = [];
    childPageNum.value = 1;
    getChildLeaf(queryPageSize);
  } else {
    suitePageNum.value = 1;
    casesOption.value = [];
    await getCaseOptions();
    // 搜索完毕之后用已经选择的项(也就是搜索是空的时候)suit-id默认展开，没有的suit-id添加到已有的列表中
    if (tempSelectedKeys.value.length) {
      let noRepeatOptions = [];
      tempSelectedOptions.value.forEach((el) => {
        if (!noRepeatOptions.find((e) => e.suiteId === el.suiteId)) {
          noRepeatOptions.push(el);
        }
      });

      noRepeatOptions.forEach((item) => {
        if (suiteIds.value.indexOf(item.suiteId) === -1) {
          casesOption.value.push(item.suite);
        }
        defaultExpandKeys.value.push(item.suiteId);
      });
    }
  }
};

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
        if (isUploadCases.value) {
          formData.append('file', formValue.value.file[0]?.file);
        } else {
          formData.append('cases', createAjax.exchangeCases(formValue.value.cases).join(','));
        }
        await updateTemplateDrawer(formData, modalData.value.id);
      } else {
        await createAjax.postForm(formValue, isUploadCases.value);
      }
      emit('onNegativeClick');
    }
  });
};

const onNegativeClick = () => {
  emit('onNegativeClick');
};
const versionResultValue = ref(null);
const getVersionSelect = (data, milestone) => {
  if (data.includes(milestone)) {
    versionResultValue.value = milestone;
  } else {
    let lastIndex = milestone.lastIndexOf('-');
    let result = milestone.substring(0, lastIndex);
    getVersionSelect(data, result);
  }
};
onMounted(async () => {
  getProductOptions();
  if (isEditTemplate.value) {
    formValue.value.product = modalData.value.milestone.split('-')[0];
    await getVersionOpts(versionOpts, formValue.value.product);
    formValue.value.name = modalData.value.name;
    formValue.value.permission_type = modalData.value.template_type;
    formValue.value.description = modalData.value.description;
    formValue.value.git_repo_id = String(modalData.value.git_repo.id);
    changeRepo(formValue.value.git_repo_id);
    formValue.value.cases = modalData.value?.cases?.map((item) => {
      return `case-${item.id}`;
    });
    // 先从 modalData.value.milestone的最后截取然后看版本列表中有没有同名的，如果有就是此版本，如果没有则继续向前截取对比，直到取到版本名
    let mileIndex = modalData.value.milestone.indexOf('-') + 1;
    let mileResult = modalData.value.milestone.substring(mileIndex);
    let labels = [];
    versionOpts.value.map((item) => labels.push(item.label));
    getVersionSelect(labels, mileResult);
    formValue.value.version = versionOpts.value.filter(
      (item) => item.label === versionResultValue.value
    )[0].value;
    // 获取里程碑列表
    // await getMilestoneOpts(milestoneOpts, formValue.value.version);
    formValue.value.milestone_id = modalData.value.milestone_id.toString();
  }
});

onUnmounted(() => {
  clean();
});
</script>
<style lang="less">
.modalTransfer .n-transfer-list--source {
  .n-transfer-list-header__button {
    display: none;
  }
}
</style>
<style scoped>
.case-switch {
  position: absolute;
  top: -30px;
  left: 110px;
}
</style>
