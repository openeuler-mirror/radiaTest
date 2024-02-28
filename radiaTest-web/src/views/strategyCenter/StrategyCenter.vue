<template>
  <div v-show="!isDesignTemplate" style="height: 100%">
    <n-spin :show="showLoading" stroke="rgba(0, 47, 167, 1)" class="spin-box">
      <n-layout has-sider style="height: 100%">
        <n-layout-sider
          bordered
          content-style="padding: 24px;overflow-y:auto;"
          :collapsed-width="1"
          :width="400"
          show-trigger="arrow-circle"
        >
          <n-tree
            style="height: 100%"
            block-line
            :data="treeData"
            :default-expanded-keys="defaultExpandedKeys"
            :render-prefix="renderPrefix"
            :render-suffix="renderSuffix"
            :node-props="nodeProps"
            @load="loadTreeData"
          />
          <n-dropdown
            trigger="manual"
            placement="bottom-start"
            :show="showDropdown"
            :options="dropdownOptions"
            :x="dropdownX"
            :y="dropdownY"
            @select="handleDropdownSelect"
            @clickoutside="handleDropdownClickoutside"
          />
        </n-layout-sider>
        <n-layout-content content-style="padding: 24px;height:100%" id="strategyCenterRight">
          <StrategyContent
            v-if="showStrategy"
            :currentFeature="currentFeature"
            @submitPullRequestCb="submitPullRequestCb"
          ></StrategyContent>
          <FeatureSetDetail
            ref="FeatureSetDetailRef"
            :currentFeature="currentFeature"
            v-else
          ></FeatureSetDetail>
        </n-layout-content>
      </n-layout>
      <n-modal v-model:show="showInputFeatureModal" :mask-closable="false">
        <n-card
          :title="createTitle('录入特性')"
          size="large"
          :bordered="false"
          :segmented="{
            content: true,
          }"
          style="width: 1000px"
        >
          <n-form
            label-placement="left"
            :label-width="80"
            :model="inputFeatureFormValue"
            :rules="inputFeatureFormRules"
            size="medium"
            ref="inputFeatureFormRef"
          >
            <n-grid :cols="12">
              <n-form-item-gi :span="8" label="特性名" path="feature">
                <n-input v-model:value="inputFeatureFormValue.feature" placeholder="请输入特性名" />
              </n-form-item-gi>
              <n-form-item-gi :span="4" label="特性编号" path="no">
                <n-input v-model:value="inputFeatureFormValue.no" placeholder="请输入特性编号" />
              </n-form-item-gi>
              <n-form-item-gi :span="6" label="release to" path="release_to">
                <n-input
                  v-model:value="inputFeatureFormValue.release_to"
                  placeholder="请输入特性release_to"
                />
              </n-form-item-gi>
              <n-form-item-gi :span="6" label="拥有者" path="owner">
                <n-dynamic-tags v-model:value="inputFeatureFormValue.owner" />
              </n-form-item-gi>
              <n-form-item-gi :span="6" label="特性包" path="pkgs">
                <n-input v-model:value="inputFeatureFormValue.pkgs" placeholder="请输入特性包" />
              </n-form-item-gi>
              <n-form-item-gi :span="6" label="sig组" path="sig">
                <n-dynamic-tags v-model:value="inputFeatureFormValue.sig" />
              </n-form-item-gi>
              <n-form-item-gi :span="4" label="任务ID" path="task_id">
                <n-input
                  disabled
                  v-model:value="inputFeatureFormValue.task_id"
                  placeholder="请输入任务ID"
                />
              </n-form-item-gi>
              <n-form-item-gi :span="8" label="URL" path="url">
                <n-input v-model:value="inputFeatureFormValue.url" placeholder="请输入URL" />
              </n-form-item-gi>
            </n-grid>
          </n-form>
          <n-space>
            <n-button size="medium" type="error" @click="cancelInputFeature" ghost> 取消 </n-button>
            <n-button size="medium" type="primary" @click="submitInputFeature" ghost>
              提交
            </n-button>
          </n-space>
        </n-card>
      </n-modal>
      <n-modal v-model:show="showRelateFeatureModal" :mask-closable="false">
        <n-card
          :title="createTitle('关联特性')"
          size="large"
          :bordered="false"
          :segmented="{
            content: true,
          }"
          style="width: 500px"
        >
          <n-form
            label-placement="left"
            :label-width="80"
            :model="relateFeatureFormValue"
            :rules="relateFeatureFormRules"
            size="medium"
            ref="relateFeatureFormRef"
          >
            <n-grid :cols="12">
              <n-form-item-gi :span="12" label="关联特性" path="featureName">
                <n-select
                  v-model:value="relateFeatureFormValue.featureName"
                  placeholder="请选择关联特性"
                  :options="relateFeatureOptions"
                  filterable
                  clearable
                />
              </n-form-item-gi>
            </n-grid>
          </n-form>
          <n-space>
            <n-button size="medium" type="error" @click="cancelRelateFeature" ghost>
              取消
            </n-button>
            <n-button size="medium" type="primary" @click="submitRelateFeature" ghost>
              提交
            </n-button>
          </n-space>
        </n-card>
      </n-modal>

      <n-modal v-model:show="showImportFeatureModal" :mask-closable="false">
        <n-card
          :title="createTitle(`导入测试策略：${currentNode.label}`)"
          size="large"
          :bordered="false"
          :segmented="{
            content: true,
          }"
          style="width: 500px"
        >
          <n-upload
            ref="importFeatureRef"
            multiple
            v-model:file-list="importFeatureFileList"
            :default-upload="false"
            @change="handleUploadChange"
            @before-upload="beforeUpload"
            action="/api/v1/case/import/test"
          >
            <n-upload-dragger>
              <div style="margin-bottom: 12px">
                <n-icon size="48" :depth="3">
                  <archive-icon />
                </n-icon>
              </div>
              <n-text style="font-size: 16px">点击或者拖动文件到该区域来上传</n-text>
              <n-p depth="3" style="margin: 8px 0 0 0"> 仅支持导入md、markdown格式的文件 </n-p>
            </n-upload-dragger>
          </n-upload>
          <n-space>
            <n-button size="medium" type="error" @click="cancelImportFeature" ghost>
              取消
            </n-button>
            <n-button size="medium" type="primary" @click="submitImportFeature" ghost>
              提交
            </n-button>
          </n-space>
        </n-card>
      </n-modal>
      <n-modal v-model:show="showExportFeatureModal" :mask-closable="false">
        <n-card
          :title="createTitle(`导出测试策略：${currentNode.label}`)"
          size="large"
          :bordered="false"
          :segmented="{
            content: true,
          }"
          style="width: 500px"
        >
          <n-radio-group v-model:value="exportType" name="exportFeatureRadiogroup">
            <n-space>
              <n-radio value="markdown">markdown </n-radio>
              <n-radio value="yaml" disabled>yaml </n-radio>
              <n-radio value="json" disabled>json </n-radio>
            </n-space>
          </n-radio-group>
          <n-space style="margin-top: 30px">
            <n-button size="medium" type="error" @click="cancelExportFeature" ghost>
              取消
            </n-button>
            <n-button size="medium" type="primary" @click="submitExportFeature" ghost>
              提交
            </n-button>
          </n-space>
        </n-card>
      </n-modal>
    </n-spin>
  </div>
  <DesignTemplate v-show="isDesignTemplate"></DesignTemplate>
</template>

<script setup>
import { isDesignTemplate } from '@/views/taskManage/modules/manage.js';
import { Organization20Regular, Folder16Regular } from '@vicons/fluent';
import { Database } from '@vicons/fa';
import { Milestone, ChartRelationship, Locked } from '@vicons/carbon';
import { DatabaseImport, FileImport, FileExport } from '@vicons/tabler';
import { MdRefresh } from '@vicons/ionicons4';
import { ArchiveOutline as ArchiveIcon } from '@vicons/ionicons5';
import { SettingsSuggestOutlined } from '@vicons/material';
import { NIcon, NSpace, NTooltip } from 'naive-ui';
import StrategyContent from '@/views/strategyCenter/StrategyContent.vue';
import FeatureSetDetail from '@/views/strategyCenter/FeatureSetDetail.vue';
import DesignTemplate from '@/views/strategyCenter/DesignTemplate.vue';
import { createTitle } from '@/assets/utils/createTitle';
import { getProductVersionOrgOpts } from '@/assets/utils/getOpts';
import { storage } from '@/assets/utils/storageUtils';
import { getAllFeature, getProductFeature } from '@/api/get';
import { relateProductFeature, createProductFeature } from '@/api/post';
import _ from 'lodash';

const showLoading = ref(false);
const treeData = ref([]);
const currentNode = ref(null); // 当前选中节点
const currentFeature = ref(null); // 当前选中特性
const showStrategy = ref(false); // 展示特性集或测试策略
const productList = ref([]); // 产品版本列表
const orgList = ref([]);
const defaultExpandedKeys = ref([]);
const FeatureSetDetailRef = ref(null); // 特性集页面

// 获取组织节点
const getOrgList = () => {
  let item = {
    label: storage.getLocalValue('unLoginOrgId').name,
    key: storage.getLocalValue('unLoginOrgId').id,
    info: {
      org_id: storage.getLocalValue('unLoginOrgId').id,
    },
    isLeaf: false,
    type: 'org',
    root: true,
    icon: Organization20Regular,
  };
  treeData.value = [
    {
      ...item,
      children: createOrgChildren(item),
    },
  ];
  defaultExpandedKeys.value.push(storage.getLocalValue('unLoginOrgId').id);
};

// 获取树根节点
const getRootNodes = () => {
  treeData.value = _.cloneDeep(orgList.value);
};

// 创建组织下级目录
const createOrgChildren = (orgItem) => {
  let childrenArr = [];
  childrenArr.push({
    label: '特性集',
    key: `featureSet-${orgItem.org_id}`,
    isLeaf: true,
    type: 'featureSet',
    root: false,
    icon: Database,
    info: {
      org_id: orgItem.org_id,
    },
  });
  productList.value.forEach((item) => {
    childrenArr.push({
      label: item.label,
      key: `productVersion-${item.value}`,
      isLeaf: false,
      type: 'productVersion',
      root: false,
      icon: Milestone,
      info: {
        org_id: orgItem.org_id,
        productVersionId: item.value,
      },
    });
  });
  return childrenArr;
};

// 加载树子节点
const loadTreeData = (node) => {
  return new Promise((resolve, reject) => {
    if (node.type === 'productVersion') {
      node.children = [];
      node.children.push(
        {
          label: '继承特性',
          key: `inherit-${node.info.productVersionId}`,
          isLeaf: false,
          type: 'inherit',
          root: false,
          icon: Folder16Regular,
          info: {
            org_id: node.info.org_id,
            productVersionId: node.info.productVersionId,
          },
        },
        {
          label: '新增特性',
          key: `increase-${node.info.productVersionId}`,
          isLeaf: false,
          type: 'increase',
          root: false,
          icon: Folder16Regular,
          info: {
            org_id: node.info.org_id,
            productVersionId: node.info.productVersionId,
          },
        }
      );
      resolve();
    } else if (node.type === 'inherit') {
      node.children = [];
      getProductFeature(node.info.productVersionId, { is_new: false }).then((res) => {
        res?.data?.forEach((item) => {
          node.children.push({
            label: item.feature,
            key: `inheritFeature-${node.info.productVersionId}-${item.id}`,
            isLeaf: true,
            type: 'inheritFeature',
            root: false,
            icon: SettingsSuggestOutlined,
            status: item.strategy_commit_status,
            info: {
              org_id: node.info.org_id,
              productVersionId: node.info.productVersionId,
              feature_id: item.id,
              product_feature_id: item.product_feature_id,
            },
          });
        });
      });
      resolve();
    } else if (node.type === 'increase') {
      node.children = [];
      getProductFeature(node.info.productVersionId, { is_new: true }).then((res) => {
        res?.data?.forEach((item) => {
          node.children.push({
            label: item.feature,
            key: `increaseFeature-${node.info.productVersionId}-${item.id}`,
            isLeaf: true,
            type: 'increaseFeature',
            root: false,
            icon: SettingsSuggestOutlined,
            status: item.strategy_commit_status,
            info: {
              org_id: node.info.org_id,
              productVersionId: node.info.productVersionId,
              feature_id: item.id,
              product_feature_id: item.product_feature_id,
            },
          });
        });
      });
      resolve();
    }
    reject(new Error('未知错误'));
  });
};

// 树前缀图标
const renderPrefix = ({ option }) => {
  return h(NIcon, null, { default: () => h(option.icon) });
};

// 树后缀图标
const renderSuffix = ({ option }) => {
  if (option?.status === 'submitted') {
    return h(
      NTooltip,
      { trigger: 'hover' },
      { default: () => '用户提交未合入', trigger: () => h(NIcon, null, h(Locked)) }
    );
  }
  return null;
};

// 右键菜单图标
const renderIcon = (icon) => {
  return () => {
    return h(NIcon, null, {
      default: () => h(icon),
    });
  };
};

const showDropdown = ref(false);
const dropdownOptions = ref([]);
const dropdownX = ref(0);
const dropdownY = ref(0);

// 点击右键菜单
const handleDropdownSelect = (key) => {
  showDropdown.value = false;
  if (key === 'inputFeature') {
    showInputFeatureModal.value = true;
  } else if (key === 'refresh') {
    getRootNodes();
  } else if (key === 'relateFeature') {
    showRelateFeatureModal.value = true;
    getAllFeatureFn({ type: 'inherite', paged: false });
  } else if (key === 'updateFeature') {
    // showUpdateFeatureModal.value = true;
    // updateFeatureFormValue.value.featureName = currentNode.value.label;
  } else if (key === 'importFeature') {
    showImportFeatureModal.value = true;
  } else if (key === 'exportFeature') {
    showExportFeatureModal.value = true;
  } else if (key === 'deleteFeature') {
    // showDeleteFeatureModal.value = true;
  }
};

// 关闭右键菜单
const handleDropdownClickoutside = () => {
  showDropdown.value = false;
};

// 生成右键菜单
const createMenu = (type) => {
  if (type === 'featureSet') {
    return [
      {
        label: '录入特性',
        key: 'inputFeature',
        icon: renderIcon(DatabaseImport),
      },
      {
        label: '刷新',
        key: 'refresh',
        icon: renderIcon(MdRefresh),
      },
    ];
  } else if (type === 'inherit') {
    return [
      {
        label: '关联特性',
        key: 'relateFeature',
        icon: renderIcon(ChartRelationship),
      },
      {
        label: '刷新',
        key: 'refresh',
        icon: renderIcon(MdRefresh),
      },
    ];
  } else if (type === 'increase') {
    return [
      {
        label: '刷新',
        key: 'refresh',
        icon: renderIcon(MdRefresh),
      },
    ];
  } else if (type === 'feature' || type === 'inheritFeature') {
    return [
      {
        label: '导入',
        key: 'importFeature',
        icon: renderIcon(FileImport),
      },
      {
        label: '导出',
        key: 'exportFeature',
        icon: renderIcon(FileExport),
      },

      {
        label: '刷新',
        key: 'refresh',
        icon: renderIcon(MdRefresh),
      },
    ];
  } else if (type === 'increaseFeature') {
    return [
      {
        label: '导入',
        key: 'importFeature',
        icon: renderIcon(FileImport),
      },
      {
        label: '导出',
        key: 'exportFeature',
        icon: renderIcon(FileExport),
      },

      {
        label: '刷新',
        key: 'refresh',
        icon: renderIcon(MdRefresh),
      },
    ];
  }
  return [];
};

// 点击树节点
const nodeProps = ({ option }) => {
  return {
    onClick() {
      currentNode.value = option;
      if (option.type === 'inheritFeature' || option.type === 'increaseFeature') {
        currentFeature.value = option;
        showStrategy.value = true;
      } else if (option.type === 'featureSet') {
        showStrategy.value = false;
        currentFeature.value = option;
      }
    },
    onContextmenu(e) {
      e.preventDefault();
      currentNode.value = option;
      showDropdown.value = true;
      dropdownX.value = e.clientX;
      dropdownY.value = e.clientY;
      dropdownOptions.value = createMenu(option.type);
    },
  };
};

const showInputFeatureModal = ref(false); // 显示录入特性弹框
const inputFeatureFormRef = ref(null);
const inputFeatureFormValue = ref({
  feature: null,
  no: null,
  owner: [],
  release_to: null,
  pkgs: null,
  sig: [],
  task_id: null,
  url: null,
});
const inputFeatureFormRules = ref({
  feature: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入特性名',
  },
  no: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入特性编号',
  },
});

// 取消录入特性
const cancelInputFeature = () => {
  showInputFeatureModal.value = false;
  inputFeatureFormValue.value = {
    feature: null,
    no: null,
    owner: [],
    release_to: null,
    pkgs: null,
    sig: [],
    task_id: null,
    url: null,
  };
};

// 提交录入特性
const submitInputFeature = (e) => {
  e.preventDefault();
  inputFeatureFormRef.value?.validate((errors) => {
    if (!errors) {
      createProductFeature(inputFeatureFormValue.value).then(() => {
        cancelInputFeature();
        FeatureSetDetailRef.value.getFeatureSet(1);
      });
    } else {
      console.log(errors);
    }
  });
};

const showRelateFeatureModal = ref(false); // 显示关联特性弹框
const relateFeatureFormRef = ref(null);
const relateFeatureFormValue = ref({
  featureName: null,
});
const relateFeatureFormRules = ref({
  featureName: {
    required: true,
    type: 'number',
    trigger: ['blur', 'change'],
    message: '请输入特性名',
  },
});
const relateFeatureOptions = ref([]);

// 获取特性集
const getAllFeatureFn = (param) => {
  getAllFeature(param).then((res) => {
    res.data?.forEach((item) => {
      relateFeatureOptions.value.push({
        label: item.feature,
        value: item.id,
      });
    });
  });
};

// 取消关联特性
const cancelRelateFeature = () => {
  showRelateFeatureModal.value = false;
  relateFeatureFormValue.value = {
    featureName: null,
  };
};

// 提交关联特性
const submitRelateFeature = (e) => {
  e.preventDefault();
  relateFeatureFormRef.value?.validate((errors) => {
    if (!errors) {
      relateProductFeature(currentNode.value.info.productVersionId, {
        feature_id: relateFeatureFormValue.value.featureName,
      }).then(() => {
        getRootNodes();
        cancelRelateFeature();
      });
    } else {
      console.log(errors);
    }
  });
};

const showImportFeatureModal = ref(false); // 显示导入弹框
const importFeatureRef = ref(null);
const importFeatureFileList = ref([]); // 上传文件列表

// 上传文件变更
const handleUploadChange = (data) => {
  importFeatureFileList.value = data.fileList;
};

// 限制上传文件
const beforeUpload = async (data) => {
  let fileType = data.file.name.split('.').pop();
  const supportedFiletypes = ['md', 'markdown'];
  if (!supportedFiletypes.includes(fileType)) {
    window.$message?.error('只能上传md、markdown格式的文件，请重新上传');
    return false;
  }
  return true;
};

// 取消上传
const cancelImportFeature = () => {
  showImportFeatureModal.value = false;
  importFeatureFileList.value = [];
};

// 提交上传
const submitImportFeature = () => {
  // importFeatureRef.value?.submit();
};

const showExportFeatureModal = ref(false); // 显示导出特性弹框
const exportType = ref('markdown');

// 取消导出特性
const cancelExportFeature = () => {
  showExportFeatureModal.value = false;
  exportType.value = 'markdown';
};

// 提交导出特性
const submitExportFeature = () => {
  console.log(exportType.value);
};

// 提交PR回调
const submitPullRequestCb = () => {
  getRootNodes();
};

onMounted(async () => {
  isDesignTemplate.value = false;
  await getProductVersionOrgOpts(productList); // 获取产品版本列表
  getOrgList();
});
</script>

<style scoped lang="less">
.spin-box {
  height: 100%;

  :deep(.n-spin-content) {
    height: 100%;
  }
}
</style>
