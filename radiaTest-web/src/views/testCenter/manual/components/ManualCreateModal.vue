<template>
  <n-modal v-model:show="showModal" :mask-closable="false">
    <vue3-draggable-resizable
      v-model:x="x"
      v-model:y="y"
      :draggable="draggable"
      :resizable="false"
      style="border-style: none"
    >
      <div class="dragArea" @mouseenter="draggable = true" @mouseleave="draggable = false"></div>
      <n-card class="modalCard" style="min-width: 680px; max-width: 1280px">
        <n-card
          :title="createTitle('创建手工测试任务')"
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
                <n-form-item-gi :span="12" label="任务名" path="name">
                  <n-input v-model:value="formValue.name" placeholder="请输入任务名" />
                </n-form-item-gi>
                <n-form-item-gi :span="6" label="类型" path="permission_type">
                  <n-cascader
                    v-model:value="formValue.permission_type"
                    placeholder="请选择"
                    :options="typeOptions"
                    :on-load="handleLoad"
                    check-strategy="child"
                    remote
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
                <n-form-item-gi :span="12" label="里程碑" path="milestone_id">
                  <n-select
                    v-model:value="formValue.milestone_id"
                    placeholder="请选择里程碑"
                    :options="milestoneOpts"
                    clearable
                  />
                </n-form-item-gi>
                <n-form-item-gi :span="4" label="" path="case_automatic">
                  <n-checkbox
                    v-model:checked="formValue.case_automatic"
                    @update:checked="() => getBaseLines()"
                  >
                    是否为手工用例
                  </n-checkbox>
                </n-form-item-gi>

                <n-form-item-gi :span="24" label="绑定测试用例" path="cases">
                  <n-transfer
                    class="modalTransfer"
                    ref="transfer"
                    select-all-text=""
                    v-model:value="formValue.cases"
                    :options="flattenTree(casesOption.concat(searchOption))"
                    :render-source-list="renderSourceList"
                    target-filterable
                  />
                </n-form-item-gi>
              </n-grid>
            </n-form>
          </div>
        </n-card>
        <n-space>
          <n-button size="large" type="error" @click="onNegativeClick" ghost> 取消 </n-button>
          <n-button size="large" type="primary" @click="onPositiveClick" ghost> 提交 </n-button>
        </n-space>
      </n-card>
    </vue3-draggable-resizable>
  </n-modal>
</template>

<script setup>
import Vue3DraggableResizable from 'vue3-draggable-resizable';
import 'vue3-draggable-resizable/dist/Vue3DraggableResizable.css';
import { NTree, NInput, NScrollbar, useMessage } from 'naive-ui';
import config from '@/assets/config/dragableResizable.js';
import { createTitle } from '@/assets/utils/createTitle';
import { createManualJob } from '@/api/post';
import { getCasesNode, getManualCaseBySearch, getBaselineByMilestone } from '@/api/get';
import extendForm from '@/views/versionManagement/product/modules/createForm.js';
import _ from 'lodash';
import { getVersionOpts, getProductOpts } from '@/assets/utils/getOpts';
import axios from '@/axios';

import manual from '@/views/testCenter/manual/modules/manual';
const queryPageSize = 20;
const message = useMessage();
const emit = defineEmits(['updateTable']);
const props = defineProps({
  initX: {
    default: 400,
    type: Number,
  },
  initY: {
    default: 200,
    type: Number,
  },
});
const x = ref(props.initX);
const y = ref(props.initY);
const showModal = ref(false);
const { draggable } = toRefs(config);
const formRef = ref(null);
const formValue = ref({
  name: '',
  product: undefined,
  version: undefined,
  milestone_id: null,
  cases: [],
  groups: undefined,
  case_automatic: true,
});
const rules = ref({
  name: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入任务名',
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
  case_id: {
    required: true,
    type: 'number',
    trigger: ['blur', 'change'],
    message: '请选择用例',
  },
  milestone_id: {
    required: true,
    message: '请绑定里程碑',
    trigger: ['blur'],
  },
  cases: {
    required: true,
    type: 'array',
    trigger: ['blur', 'change'],
    message: '测试用例',
  },
});
// 类型
const typeOptions = ref([
  { label: '组织', value: 'org', isLeaf: true },
  { label: '团队', value: 'group', isLeaf: false },
  { label: '个人', value: 'person', isLeaf: true },
]);
const productOpts = ref([]); // 产品
const getProductOptions = async () => {
  getProductOpts(productOpts);
};

const handleLoad = extendForm.handleLoad;
// 版本
const versionOpts = ref([]);
watch(
  () => formValue.value.product,
  () => {
    getVersionOpts(versionOpts, formValue.value.product);
  }
);

// 里程碑
const milestoneOpts = ref([]);
watch(
  () => formValue.value.version,
  () => {
    getMilestoneFilterOpts();
  }
);
const getMilestoneFilterOpts = () => {
  milestoneOpts.value = [];
  axios
    .get('/v1/milestone/preciseget', {
      product_id: formValue.value.version,
    })
    .then((res) => {
      res.data = res.data.filter((item) => item.has_baseline);
      res.data.forEach((item) => {
        milestoneOpts.value.push({
          label: item.name,
          value: item.id.toString(),
        });
      });
    })
    .catch(() => {
      window.message?.error('无法连接服务器，获取里程碑选项失败');
    });
};
// 根据里程碑的选择获取基线
const casesOption = ref([]);
watch(
  () => formValue.value.milestone_id,
  () => {
    getBaseLines();
  }
);
const searchCaseId = ref(null);
const getBaseLines = () => {
  casesOption.value = [];
  searchOption.value = [];
  formValue.value.cases = [];
  formValue.value.milestone_id &&
    getBaselineByMilestone({ milestone_id: formValue.value.milestone_id })
      .then((res) => {
        searchCaseId.value = res.data.id || null;
        getChildLeaf(res.data.root_case_node_id);
      })
      .catch(() => {});
};

// ************穿梭框************
const flattenTree = (list) => {
  const result = [];
  function flatten(_list = []) {
    _list.forEach((item) => {
      result.push(item);
      item.children && flatten(item.children);
    });
  }
  flatten(list);
  return result;
};
const patternValue = ref(null);
const searchTreeDisplay = ref({
  maxHeight: '200px',
  marginTop: '38px',
  display: 'none',
});
const treeDisplay = ref({
  maxHeight: '200px',
  marginTop: '38px',
  display: 'block',
});
const renderSourceList = ({ onCheck }) => {
  return [
    h(NInput, {
      size: 'small',
      style: { margin: '5px 0 5px 10px', width: '96%' },
      placeholder: '请输入',
      value: patternValue.value,
      onInput: handleFilter,
    }),
    h(
      NScrollbar,
      {
        style: treeDisplay.value,
      },
      [
        h(NTree, {
          keyField: 'value',
          checkable: true,
          selectable: false,
          blockLine: true,
          cascade: true,
          checkStrategy: 'child',
          showIrrelevantNodes: false,
          data: casesOption.value,
          onLoad: handleTreeLoad,
          checkedKeys: formValue.value.cases,
          allowCheckingNotLoaded: true,
          expandOnClick: true,
          onUpdateCheckedKeys: async (checkedKeys, options, node) => {
            let newCheckedKeys = _.cloneDeep(checkedKeys);
            if (node.action === 'check') {
              let isCase = newCheckedKeys.every((item) => item.startsWith('case'));
              if (!isCase) {
                message.warning('节点未展开至用例层的将不会被选中！');
              }

              newCheckedKeys = newCheckedKeys.filter((item) => item.startsWith('case'));
            }
            onCheck(newCheckedKeys);
          },
        }),
      ]
    ),
    h(
      NScrollbar,
      {
        style: searchTreeDisplay.value,
        onScroll: handleScrollBar,
      },
      [
        h(NTree, {
          keyField: 'value',
          checkable: true,
          selectable: false,
          blockLine: true,
          cascade: true,
          checkStrategy: 'child',
          showIrrelevantNodes: false,
          data: searchOption.value,
          checkedKeys: formValue.value.cases,
          allowCheckingNotLoaded: true,
          expandOnClick: true,
          onUpdateCheckedKeys: async (checkedKeys) => {
            onCheck(checkedKeys);
          },
        }),
      ]
    ),
  ];
};

// 异步加载树子节点
const handleTreeLoad = (node) => {
  return new Promise((resolve) => {
    getChildLeaf(node, resolve);
  });
};
const getCaseType = (item) => {
  if (item.type === 'case' && item.case_automatic) {
    return ' （自动化）';
  } else if (item.type === 'case' && !item.case_automatic) {
    return ' （手工）';
  }
  return '';
};
const getChildLeaf = async (node, resolve) => {
  await getCasesNode(node.info?.id || node)
    .then(async (res) => {
      let keyItem;
      let leaf = [];
      if (res.data.type === 'suite' && res.data.children.length) {
        res.data.children = res.data.children.filter((item) => {
          if (formValue.value.case_automatic) {
            return !item.case_automatic;
          }
          return item;
        });
      }
      for (const item of res.data.children) {
        let tag = getCaseType(item);
        keyItem = {
          label: `${item.title}${tag}`,
          info: item,
          key: `${item.type}-${item.case_id || item.id}`,
          value: `${item.type}-${item.case_id || item.id}`,
          isLeaf: item.type === 'case',
          type: item.type,
          suiteId: item.suite_id,
          caseId: item.case_id,
        };
        leaf.push(keyItem);
      }
      if (resolve) {
        // 点击树节点展开叶子
        node.children = leaf;
        resolve && resolve();
      } else {
        casesOption.value = leaf;
      }
    })
    .catch(() => {});
};

// 穿梭框异步查询
const childPageNum = ref(1);
const leafArray = ref([]);
const handleFilter = async (pattern) => {
  //请求接口返回的树数据逻辑
  patternValue.value = pattern.trim();
  if (pattern.trim()) {
    searchTreeDisplay.value.display = 'block';
    treeDisplay.value.display = 'none';
    leafArray.value = [];
    childPageNum.value = 1;
    await getSearchLeaf(20);
  } else {
    treeDisplay.value.display = 'block';
    searchTreeDisplay.value.display = 'none';
  }
};
const hasChildNext = ref(false);
const searchOption = ref([]);

const getSearchLeaf = async (pageSize) => {
  let params = {
    paged: true,
    page_num: childPageNum.value,
    page_size: pageSize,
    name: patternValue.value,
    baseline_id: searchCaseId.value,
    automatic: !formValue.value.case_automatic,
  };
  await getManualCaseBySearch(params)
    .then((res) => {
      let keyItem;
      res.data.items.length &&
        res.data.items.forEach((item) => {
          keyItem = {
            label: item.name,
            value: `case-${item.id}`,
            key: `case-${item.id}`,
            isLeaf: true,
            suiteId: `suite-${item.suite_id}`,
            type: 'case',
          };
          leafArray.value.push(keyItem);
        });

      //搜索的时候返回的叶子
      searchOption.value = leafArray.value;
      hasChildNext.value = res.data.has_next;
      if (res.data.has_next) {
        childPageNum.value = res.data.next_num;
      }
    })
    .catch(() => {});
};
// 滚动异步加载
const handleScrollBar = (e) => {
  const currentTarget = e.currentTarget;
  if (currentTarget.scrollTop + currentTarget.offsetHeight >= currentTarget.scrollHeight) {
    if (hasChildNext.value) {
      getSearchLeaf(queryPageSize);
    }
  }
};
const exchangeCases = (cases) => {
  return cases?.map((item) => {
    return item.replace('case-', '');
  });
};
// 取消按钮
const onNegativeClick = () => {
  showModal.value = false;
  formValue.value = {
    name: '',
    product: undefined,
    version: undefined,
    milestone_id: null,
    cases: [],
    case_automatic: true,
  };
  casesOption.value = [];
  searchOption.value = [];
};
// 确定按钮
const onPositiveClick = () => {
  formRef.value?.validate((errors) => {
    if (!errors) {
      createManualJob({
        cases: formValue.value.cases.length && exchangeCases(formValue.value.cases).join(','),
        name: formValue.value.name,
        milestone_id: formValue.value.milestone_id,
        permission_type: formValue.value.permission_type,
      }).then(() => {
        onNegativeClick();
        manual.executeRef.value.getData();
        emit('updateTable');
      });
    } else {
      window.$message?.error('请检查输入合法性');
    }
  });
};
onMounted(() => {
  treeDisplay.value.display = 'block';
  getProductOptions();
});

defineExpose({
  showModal,
});
</script>
<style lang="less">
.modalTransfer .n-transfer-list--source {
  .n-transfer-list-header__button {
    display: none;
  }
}
</style>
<style scoped lang="less">
.modalCard {
  z-index: 2;
}
.dragArea {
  position: absolute;
  height: 60px;
  width: 100%;
  z-index: 3;
  &:hover {
    cursor: grab;
  }
}
</style>
