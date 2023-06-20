<template>
  <div class="baselineTemplate">
    <div class="baselineTemplate-left">
      <n-button
        style="width: 100%"
        size="small"
        type="success"
        dashed
        @click="
          () => {
            showCreateModal = true;
          }
        "
      >
        新建模板
      </n-button>
      <n-input clearable type="text" size="small" v-model:value="searchWords">
        <template #prefix>
          <n-icon color="666666" :component="Search" />
        </template>
      </n-input>
      <div
        v-for="(item, index) in templateList"
        :key="index"
        :class="[{ active: checkedItem.id === item.id }, 'templateItem']"
        @click="handleTemplateClick(item)"
      >
        <div class="prefix">
          <n-icon v-if="item.openable" size="20">
            <DocumentSharp />
          </n-icon>
          <n-icon v-else color="#c4c4c4" size="20">
            <DocumentLockSharp />
          </n-icon>
          <span> {{ item.title }} </span>
        </div>
        <div class="suffix">
          <n-space>
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button
                  text
                  @click="
                    () => {
                      showEditModal = true;
                    }
                  "
                >
                  <n-icon :size="14" :component="Edit" />
                </n-button>
              </template>
              编辑
            </n-tooltip>
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button
                  text
                  @click="
                    () => {
                      showDeleteModal = true;
                    }
                  "
                >
                  <n-icon :size="14" :component="Close" />
                </n-button>
              </template>
              删除
            </n-tooltip>
          </n-space>
        </div>
      </div>
    </div>
    <n-spin class="baselineTemplate-right" :show="showBaselineTemplateSpin">
      <div v-if="templateDetail">
        <div class="top">
          <div class="txts">
            <n-icon size="16" color="#666666">
              <Cubes />
            </n-icon>
            {{ checkedItem.title }}
          </div>
          <n-space>
            <n-button type="error" ghost @click="handleCleanButtonClick"> 清空 </n-button>
            <n-button type="primary" ghost @click="handleInheritButtonClick"> 继承 </n-button>
          </n-space>
        </div>
        <n-tree
          block-line
          :data="baselineTreeData"
          expand-on-click
          :expanded-keys="baselineTreeExpandedKeys"
          :on-update:expanded-keys="updateExpandedKeys"
          :node-props="baselineTreeNodeProps"
          :render-prefix="renderBaselineTreePrefix"
          class="baseline-tree-wrap"
        />
        <n-dropdown
          style="min-width: 140px"
          placement="bottom-start"
          trigger="manual"
          :x="x"
          :y="y"
          :options="options"
          :show="showDropdown"
          :on-clickoutside="onClickoutside"
          @select="handleSelect"
        />
      </div>
      <div class="baselineTemplate-empty" v-else>
        <n-empty />
      </div>
    </n-spin>
    <n-modal v-model:show="showCreateModal" preset="card" style="width: 600px" title="创建新模板" :bordered="false">
      <n-form ref="formRef" inline :model="createForm" :rules="rules">
        <n-form-item label="标题" path="title">
          <n-input style="width: 400px" clearable v-model:value="createForm.title" />
        </n-form-item>
        <n-form-item label="是否公开可见" path="openable">
          <n-switch v-model:value="createForm.openable">
            <template #checked> 公开 </template>
            <template #unchecked> 私有 </template>
          </n-switch>
        </n-form-item>
      </n-form>
      <n-space>
        <n-button type="error" @click="onNegativeClick" ghost> 取消 </n-button>
        <n-button type="primary" @click="onPositiveClick" ghost> 提交 </n-button>
      </n-space>
    </n-modal>
    <n-modal v-model:show="showEditModal" preset="card" style="width: 600px" title="编辑基线模板" :bordered="false">
      <n-form ref="editFormRef" inline :model="editForm" :rules="editRules">
        <n-form-item label="标题" path="title">
          <n-input style="width: 400px" clearable v-model:value="editForm.title" />
        </n-form-item>
        <n-form-item label="是否公开可见" path="openable">
          <n-switch v-model:value="editForm.openable">
            <template #checked> 公开 </template>
            <template #unchecked> 私有 </template>
          </n-switch>
        </n-form-item>
      </n-form>
      <n-space>
        <n-button type="error" @click="cancelEditCallback" ghost> 取消 </n-button>
        <n-button type="primary" @click="submitEditCallback" ghost> 提交 </n-button>
      </n-space>
    </n-modal>
    <n-modal
      v-model:show="showDeleteModal"
      type="warning"
      preset="dialog"
      :title="`删除：${checkedItem?.title}`"
      content="确认删除此基线模板吗?"
      positive-text="确认"
      negative-text="放弃"
      @positive-click="submitDeleteCallback"
      @negative-click="cancelDeleteCallback"
    />
    <n-modal v-model:show="showNodeCreateModal" preset="card" style="width: 600px" title="新增子节点" :bordered="false">
      <n-spin :show="createChildNodeLoading">
        <template #description> 创建中... </template>
        <n-radio-group v-model:value="nodeCreateForm.type" style="margin-bottom: 20px">
          <n-space>
            <n-radio value="directory" v-if="selectedNode.type !== 'suite'">目录</n-radio>
            <n-radio value="suite" v-if="selectedNode.type !== 'suite'">测试套</n-radio>
            <n-radio value="case" v-if="selectedNode.type === 'suite'">测试用例</n-radio>
          </n-space>
        </n-radio-group>
        <n-form ref="nodeCreateFormRef" :model="nodeCreateForm" :rules="nodeCreateRules">
          <n-form-item path="title" label="目录命名" v-if="nodeCreateForm.type === 'directory'">
            <n-input
              v-if="nodeCreateForm.type == 'directory'"
              style="width: 400px"
              clearable
              v-model:value="nodeCreateForm.title"
            />
          </n-form-item>
          <n-form-item
            v-if="nodeCreateForm.type !== 'directory'"
            :label="`关联${nodeCreateForm.type === 'suite' ? '测试套' : '测试用例'}`"
            path="case_node_ids"
          >
            <n-tree-select
              v-if="nodeCreateForm.type === 'suite'"
              v-model:value="nodeCreateForm.case_node_ids"
              :options="casesetNodeOptions"
              :show-path="true"
              :on-load="handleCasesetOptionsLoad"
              multiple
              cascade
              checkable
              max-tag-count="responsive"
              clearable
              :placeholder="`请确保选后清单中含有${nodeCreateForm.type === 'suite' ? '测试套' : '测试用例'}`"
            />
            <n-tree-select
              v-else
              v-model:value="nodeCreateForm.case_node_ids"
              :options="suiteCaseOptions"
              :loading="suiteCaseLoading"
              multiple
              cascade
              checkable
              filterable
              clearable
              :max-tag-count="5"
              check-strategy="child"
            />
          </n-form-item>
        </n-form>
        <n-space>
          <n-button
            type="error"
            @click="
              () => {
                showNodeCreateModal = false;
              }
            "
            ghost
          >
            取消
          </n-button>
          <n-button type="primary" @click="createChildNode" ghost> 提交 </n-button>
        </n-space>
      </n-spin>
    </n-modal>
    <n-modal
      v-model:show="showNodeDeleteModal"
      type="warning"
      preset="dialog"
      :title="`删除：${selectedNode?.text}`"
      content="确认删除此节点吗?"
      positive-text="确认"
      negative-text="放弃"
      @positive-click="submitNodeDeleteCallback"
      @negative-click="cancelNodeDeleteCallback"
    />
    <n-modal v-model:show="showNodeEditModal" preset="card" style="width: 600px" title="编辑节点" :bordered="false">
      <n-form ref="nodeEditFormRef" :model="nodeEditForm" :rules="nodeEditRules">
        <n-form-item label="标题" path="title">
          <n-input clearable v-model:value="nodeEditForm.title" />
        </n-form-item>
      </n-form>
      <n-space>
        <n-button type="error" @click="cancelNodeEditCallback" ghost> 取消 </n-button>
        <n-button type="primary" @click="submitNodeEditCallback" ghost> 提交 </n-button>
      </n-space>
    </n-modal>
    <n-modal
      v-model:show="showCleanModal"
      type="warning"
      preset="dialog"
      :title="`清空${checkedItem?.title}`"
      content="确认清空此基线模板吗？清空过程不可逆"
      positive-text="确认"
      negative-text="放弃"
      @positive-click="submitCleanCallback"
      @negative-click="cancelCleanCallback"
    />
    <n-modal v-model:show="showInheritModal" preset="card" style="width: 600px" :bordered="false">
      <div class="inherit-selector">
        <span>选择将要继承的基线模板</span>
        <n-tree-select
          clearable
          v-model:value="inheriteeId"
          :options="inheritOptions"
          :show-path="true"
          :on-load="handleInheritSelectLoad"
          :render-prefix="handleRenderPrefix"
        />
      </div>
      <div class="inherit-icon-container">
        <n-icon :size="24" :color="inheriteeId ? '#40bb00' : '#c4c4c4'" :component="AngleDoubleDown" />
      </div>
      <div class="inherit-selector">
        <span>当前基线模板</span>
        <n-select :disabled="true" :value="`${checkedItem.title}`" />
      </div>
      <n-space>
        <n-button type="error" @click="cancelInheritCallback" ghost> 取消 </n-button>
        <n-button :disabled="!inheriteeId" type="primary" @click="submitInheritCallback" ghost> 提交 </n-button>
      </n-space>
    </n-modal>
  </div>
</template>

<script setup>
import { useMessage, NIcon, NTag } from 'naive-ui';
import { DocumentSharp, DocumentLockSharp, Close } from '@vicons/ionicons5';
import { Cubes, Edit, AngleDoubleDown } from '@vicons/fa';
import { Search, File } from '@vicons/tabler';
import { Box16Regular, Folder16Regular, Organization20Regular } from '@vicons/fluent';
import { Milestone } from '@vicons/carbon';
import { GroupsFilled } from '@vicons/material';
import {
  getBaselineTemplates,
  getBaselineTemplateItem,
  getBaseNode,
  getCaseSetNodes,
  getCaseNode,
  getUserInfo,
  getOrgGroup
} from '@/api/get';
import { addBaselineTemplate, addBaseNode, inheritBaselineTemplate } from '@/api/post';
import { updateBaselineTemplate, updateBaseNode } from '@/api/put';
import { deleteBaselineTemplate, deleteBaseNode, cleanBaselineTemplate } from '@/api/delete';
import { storage } from '@/assets/utils/storageUtils';

const props = defineProps({ type: String, nodeId: Number });

const message = useMessage();
const router = useRoute();

const iconType = {
  baseline: Milestone,
  directory: Folder16Regular,
  suite: Box16Regular,
  case: File
};

const options = ref([]);
const showDropdown = ref(false);
const x = ref(0);
const y = ref(0);
const selectedNode = ref(null); // 当前操作的节点信息

const casesetNodeOptions = ref([]);

const showNodeCreateModal = ref(false);
const showNodeDeleteModal = ref(false);
const showNodeEditModal = ref(false);

const nodeCreateForm = ref({
  title: undefined,
  case_node_ids: undefined,
  type: 'directory'
});
const nodeEditForm = ref({
  title: undefined
});

const searchWords = ref();
const templateDetail = ref();
const templateList = ref([]);
const checkedItem = ref({}); // 当前选择的基线模板信息

const showCreateModal = ref(false);
const createForm = ref({
  title: undefined,
  openable: false
});
const editForm = ref({
  title: undefined,
  openable: false
});
const showEditModal = ref(false);
function cancelEditCallback() {
  showEditModal.value = false;
}
const showDeleteModal = ref(false);

const showCleanModal = ref(false);
const showInheritModal = ref(false);

const inheriteeId = ref();
const inheritOptions = ref([]);

function handleInheritSelectLoad(option) {
  let params = {};
  if (option.type === 'org') {
    params.org_id = option.info.org_id;
  } else if (option.type === 'group') {
    params.group_id = option.info.group_id;
  }
  return getBaselineTemplates(params).then((res) => {
    const { data } = res;
    const childrenOptions = data.map((item) => {
      return {
        label: item.title,
        key: item.id,
        isLeaf: true,
        type: 'template'
      };
    });
    option.children = childrenOptions;
  });
}

function renderHeaderIcon(_type) {
  const _icon = iconType[_type];
  if (_icon) {
    return h(
      NIcon,
      {
        size: 15
      },
      {
        default: () => h(_icon)
      }
    );
  }
  return h(
    NIcon,
    {
      size: 15
    },
    {
      default: () => h(Folder16Regular)
    }
  );
}

function renderRelativeHeader(node) {
  return h(
    'div',
    {
      style: 'padding: 10px;'
    },
    [
      h(NTag, { size: 'small' }, node.type),
      h(
        'div',
        {
          style: {
            display: 'flex',
            alignItems: 'center',
            marginTop: '5px'
          }
        },
        [
          renderHeaderIcon(node.type),
          h(
            'div',
            {
              style: 'margin-left: 5px;'
            },
            node.title
          )
        ]
      )
    ]
  );
}

function renderOptions(node) {
  const _options = [
    {
      key: 'header',
      type: 'render',
      render: () => renderRelativeHeader(node)
    },
    {
      key: 'header-divider',
      type: 'divider'
    }
  ];
  if (node.type === 'baseline') {
    _options.push({
      label: '新增子节点',
      key: 'addChildNode'
    });
  } else if (node.type === 'directory') {
    _options.push({
      label: '新增子节点',
      key: 'addChildNode'
    });
    _options.push({
      label: '编辑节点',
      key: 'editNode'
    });
    _options.push({
      label: '删除节点',
      key: 'removeNode'
    });
  } else if (node.type === 'suite') {
    _options.push({
      label: '新增子节点',
      key: 'addChildNode'
    });
    _options.push({
      label: '删除节点',
      key: 'removeNode'
    });
  } else {
    _options.push({
      label: '删除节点',
      key: 'removeNode'
    });
  }
  return _options;
}

const currentCaseNodeId = ref(null);
const suiteCaseOptions = ref([]);

// 基线模板树前缀图标
const renderBaselineTreePrefix = ({ option }) => {
  return renderHeaderIcon(option.info.type);
};

const setChildrenData = (arr) => {
  return arr?.map((item) => {
    return {
      label: item?.data.text,
      key: item?.data.id,
      children: item?.children.length ? setChildrenData(item.children) : [],
      info: item
    };
  });
};

// 基线模板树数据
const baselineTreeData = computed(() => {
  return [
    {
      label: templateDetail.value?.data.text,
      key: templateDetail.value?.data.id,
      children: setChildrenData(templateDetail.value?.children),
      info: templateDetail.value
    }
  ];
});

// 点击基线模板树节点
const baselineTreeNodeProps = ({ option }) => {
  return {
    onClick() {},
    onContextmenu(e) {
      e.preventDefault();
      selectedNode.value = option.info.data;
      getBaseNode(selectedNode.value.id).then((res) => {
        selectedNode.value.type = res.data.type;
        options.value = renderOptions(res.data);
        currentCaseNodeId.value = res.data.case_node_id;
        nextTick(() => {
          showDropdown.value = true;
          x.value = e.clientX;
          y.value = e.clientY;
        });
      });
    }
  };
};

const baselineTreeExpandedKeys = ref([]);

const updateExpandedKeys = (keys) => {
  baselineTreeExpandedKeys.value = keys;
};

function onClickoutside() {
  showDropdown.value = false;
}

function handleCasesetOptionsLoad(option) {
  return getCaseNode(option.key).then((res) => {
    option.children = res.data.children.map((item) => {
      return {
        label: item.title,
        key: item.id,
        depth: option.depth + 1,
        isLeaf: item.type === nodeCreateForm.value.type,
        ...item
      };
    });
  });
}

function editNodeFunc() {
  showNodeEditModal.value = true;
  nodeEditForm.value.title = selectedNode.value.text;
  showDropdown.value = false;
}
function removeNodeFunc() {
  showNodeDeleteModal.value = true;
}
function addChildNodeFunc() {
  showNodeCreateModal.value = true;
  showDropdown.value = false;
  nodeCreateForm.value = {
    title: null,
    case_node_ids: null,
    type: selectedNode.value.type === 'suite' ? 'case' : 'directory'
  };
  if (nodeCreateForm.value.type === 'case') {
    suiteCaseLoading.value = true;
    getCaseNode(currentCaseNodeId.value).then((res) => {
      suiteCaseLoading.value = false;
      suiteCaseOptions.value = [{ label: '全选', key: 'allSelected', children: [] }];
      suiteCaseOptions.value[0].children = res.data.children.map((item) => {
        return {
          label: item.title,
          key: item.id
        };
      });
    });
  }
}
const selectFunc = {
  editNode: editNodeFunc,
  removeNode: removeNodeFunc,
  addChildNode: addChildNodeFunc
};
function handleSelect(key) {
  const func = selectFunc[key];
  if (func) {
    func();
  }
}

function cancelDeleteCallback() {
  showDeleteModal.value = false;
}
function cancelNodeDeleteCallback() {
  showNodeDeleteModal.value = false;
}
function cancelNodeEditCallback() {
  nodeEditForm.value.title = undefined;
  showNodeEditModal.value = false;
}

function getTemplateList() {
  let params = { title: searchWords.value };
  if (props.type === 'org') {
    params.org_id = props.nodeId ? props.nodeId : window.atob(router.params.taskId);
  } else if (props.type === 'group') {
    params.group_id = props.nodeId ? props.nodeId : window.atob(router.params.taskId);
  }
  getBaselineTemplates(params).then((res) => {
    templateList.value = res.data;
    templateDetail.value = undefined;
    checkedItem.value = {};
  });
}

function submitEditCallback() {
  updateBaselineTemplate(checkedItem.value.id, editForm.value)
    .then(() => {
      message.success('修改成功');
      getTemplateList();
    })
    .finally(() => {
      showEditModal.value = false;
    });
}
function submitDeleteCallback() {
  deleteBaselineTemplate(checkedItem.value.id)
    .then(() => {
      getTemplateList();
    })
    .finally(() => {
      showDeleteModal.value = false;
    });
}

// 编辑节点
function submitNodeEditCallback() {
  updateBaseNode(selectedNode.value.id, nodeEditForm.value).then(() => {
    message.success('编辑成功');
    nodeEditForm.value.title = undefined;
    showNodeEditModal.value = false;
    getBaselineTemplateItem(checkedItem.value.id)
      .then((res) => {
        templateDetail.value = res.data;
      })
      .catch(() => {
        templateDetail.value = undefined;
      });
  });
}

// 删除节点
function submitNodeDeleteCallback() {
  deleteBaseNode(selectedNode.value.id).then(() => {
    getBaselineTemplateItem(checkedItem.value.id)
      .then((res) => {
        templateDetail.value = res.data;
      })
      .catch(() => {
        templateDetail.value = undefined;
      });
  });
}

// 清空基线模板
function submitCleanCallback() {
  cleanBaselineTemplate(checkedItem.value.id)
    .then(() => {
      getBaselineTemplateItem(checkedItem.value.id)
        .then((res) => {
          templateDetail.value = res.data;
        })
        .catch(() => {
          templateDetail.value = undefined;
        });
    })
    .finally(() => {
      showCleanModal.value = false;
    });
}
function cancelCleanCallback() {
  showCleanModal.value = false;
}

// 继承基线模板
function submitInheritCallback() {
  inheritBaselineTemplate(checkedItem.value.id, inheriteeId.value)
    .then(() => {
      getBaselineTemplateItem(checkedItem.value.id)
        .then((res) => {
          templateDetail.value = res.data;
        })
        .catch(() => {
          templateDetail.value = undefined;
        });
    })
    .finally(() => {
      showInheritModal.value = false;
    });
}
function cancelInheritCallback() {
  showInheritModal.value = false;
}

const showBaselineTemplateSpin = ref(false);

// 点击基线模板
function handleTemplateClick(item) {
  selectedNode.value = null;
  checkedItem.value = item;
  editForm.value.title = item.title;
  editForm.value.openable = item.openable;
  templateDetail.value = null;
  showBaselineTemplateSpin.value = true;
  baselineTreeExpandedKeys.value = [];
  getBaselineTemplateItem(item.id)
    .then((res) => {
      templateDetail.value = res.data;
      showBaselineTemplateSpin.value = false;
    })
    .catch(() => {
      templateDetail.value = undefined;
      showBaselineTemplateSpin.value = false;
    });
}

function cleanCreateForm() {
  createForm.value = {
    title: undefined,
    openable: false
  };
}

function onNegativeClick() {
  cleanCreateForm();
  showCreateModal.value = false;
}

function onPositiveClick() {
  let body = {
    ...createForm.value,
    type: props.type
  };
  if (props.type === 'org') {
    body.org_id = props.nodeId ? props.nodeId : window.atob(router.params.taskId);
  } else if (props.type === 'group') {
    body.group_id = props.nodeId ? props.nodeId : window.atob(router.params.taskId);
  }
  addBaselineTemplate(body)
    .then(() => {
      message.success('创建成功');
      getTemplateList();
    })
    .finally(() => {
      showCreateModal.value = false;
      cleanCreateForm();
    });
}

const createChildNodeLoading = ref(false);

function createChildNode() {
  if (!baselineTreeExpandedKeys.value.includes(selectedNode.value.id)) {
    baselineTreeExpandedKeys.value.push(selectedNode.value.id);
  }
  createChildNodeLoading.value = true;
  addBaseNode(checkedItem.value.id, {
    is_root: false,
    parent_id: selectedNode.value.id,
    ...nodeCreateForm.value
  })
    .then(() => {
      message.success('创建中……如未更新请稍后刷新页面');
      nodeCreateForm.value = {
        title: undefined,
        case_node_ids: undefined,
        type: 'directory'
      };
      getBaselineTemplateItem(checkedItem.value.id)
        .then((res) => {
          templateDetail.value = res.data;
        })
        .catch(() => {
          templateDetail.value = undefined;
        });
    })
    .finally(() => {
      createChildNodeLoading.value = false;
      showNodeCreateModal.value = false;
    });
}

function handleCleanButtonClick() {
  showCleanModal.value = true;
}

function handleRenderPrefix({ option }) {
  if (option.type === 'org') {
    return h(
      NIcon,
      { color: '#002fa7' },
      {
        default: () => h(Organization20Regular)
      }
    );
  } else if (option.type === 'group') {
    return h(
      NIcon,
      { color: '#002fa7' },
      {
        default: () => h(GroupsFilled)
      }
    );
  }
  return h(
    NIcon,
    { color: '#002fa7' },
    {
      default: () => h(File)
    }
  );
}

function handleInheritButtonClick() {
  showInheritModal.value = true;
  inheritOptions.value = [];
  getUserInfo(storage.getValue('user_id')).then((res) => {
    const { data } = res;
    data.orgs.forEach((item) => {
      if (item.re_user_org_default) {
        inheritOptions.value.push({
          label: item.org_name,
          key: `org-${item.org_id}`,
          info: {
            org_id: item.org_id
          },
          isLeaf: false,
          type: 'org',
          disabled: true
        });
      }
    });
    getOrgGroup(storage.getValue('loginOrgId'), {
      page_num: 1,
      page_size: 99999
    }).then((_res) => {
      for (const item of _res.data.items) {
        inheritOptions.value.push({
          label: item.name,
          key: `group-${item.id}`,
          isLeaf: false,
          info: {
            group_id: item.id
          },
          type: 'group',
          disabled: true
        });
      }
    });
  });
}

onMounted(() => {
  getTemplateList();
});

watch(searchWords, () => {
  getTemplateList();
});

const suiteCaseLoading = ref(false);
const setNodeOptions = (array) => {
  return array.map((item) => ({
    label: item.title,
    key: item.id,
    depth: 1,
    isLeaf: item.type === nodeCreateForm.value.type,
    ...item
  }));
};

watch(
  () => nodeCreateForm.value.type,
  () => {
    if (nodeCreateForm.value.type === 'suite') {
      getCaseSetNodes(props.type, window.atob(router.params.taskId)).then((res) => {
        casesetNodeOptions.value = [];
        for (const i in res.data) {
          casesetNodeOptions.value.push({
            label: res.data[i].name,
            key: res.data[i].name,
            isLeaf: false,
            children: setNodeOptions(res.data[i].children)
          });
        }
      });
    }
  }
);

watch(showInheritModal, () => {
  if (showInheritModal.value === false) {
    inheriteeId.value = undefined;
  }
});
</script>

<style lang="less" scoped>
.baselineTemplate {
  display: flex;
  border: 1px solid #eee;
  border-radius: 4px;
  margin-top: 20px;
  justify-content: space-between;
  min-height: 600px;
  .baselineTemplate-left {
    width: 20%;
    padding: 20px;
    border-right: 1px solid #eee;
    .title {
      font-size: 16px;
      color: #000000;
    }
    .n-input {
      margin: 10px 0;
    }
  }
  .baselineTemplate-right {
    width: 80%;
    .top {
      height: 56px;
      width: calc(100% - 40px);
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: #000000;
      font-size: 14px;
      border-bottom: 1px solid #eee;
      padding-left: 20px;
      padding-right: 20px;
      .txts {
        display: flex;
        align-items: center;
        color: #666666;
        i {
          margin-right: 5px;
        }
      }
    }

    .baseline-tree-wrap {
      padding: 20px;
    }

    .baselineTemplate-empty {
      min-height: 600px;
      display: flex;
      justify-content: center;
      align-items: center;
    }
  }
}
.templateItem {
  padding: 0 8px;
  height: 40px;
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #000;
  cursor: pointer;
  border-radius: 5px;
  margin-bottom: 10px;
  justify-content: space-between;
  &:hover,
  &.active {
    background-color: #d2daf5;
  }
  .prefix {
    display: flex;
    align-items: center;
    .n-icon {
      color: #666666;
      margin-right: 5px;
    }
    span {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
  .suffix {
    display: none;
  }
  &:hover {
    .suffix {
      display: block;
    }
  }
}
.vue-kityminder {
  .vue-kityminder-toolbar-left {
    margin-top: 20px;
    margin-left: 20px;
    top: 0 !important;
    left: 0 !important;
    .vue-kityminder-btn {
      padding: 8px 12px;
      font-size: 14px;
    }
    .vue-kityminder-ml {
      margin-left: 8px;
    }
    .vue-kityminder-control {
      padding: 8px;
    }
  }
}

.inherit-icon-container {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-bottom: 20px;
}
.inherit-selector {
  margin-bottom: 20px;
}
</style>
