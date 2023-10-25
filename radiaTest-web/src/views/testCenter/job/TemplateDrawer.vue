<template>
  <div class="containerWrap">
    <div class="titleWrap">
      <n-button @click="createTemplateBtn" size="large" type="info" strong round>
        <template #icon>
          <file-plus />
        </template>
        创建模板
      </n-button>
      <div class="menuWrap">
        <filterButton :filterRule="filterRule" @filterchange="filterchange" class="filterBtn">
        </filterButton>
        <refresh-button :size="30" @refresh="refreshTableData"> 刷新 </refresh-button>
      </div>
    </div>
    <n-data-table
      :loading="templateTableLoading"
      :columns="templateTableColumns"
      :data="templateTableData"
      :pagination="templatePagination"
      :row-key="(row) => row.id"
    />
    <n-modal v-model:show="showCreateTemplateModal" :mask-closable="false">
      <TemplateCreateForm
        @onNegativeClick="onNegativeClick"
        :isEditTemplate="isEditTemplate"
        :modalData="modalData"
      ></TemplateCreateForm>
    </n-modal>
    <n-modal v-model:show="showCloneModal">
      <n-card style="width: 50%">
        <n-card
          :title="createTitle('克隆模板')"
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
            <n-form ref="cloneForm" :model="cloneFormValue" :rules="cloneFormRule">
              <n-form-item label="模板" path="cloneTemplateId">
                <n-select :options="templateList" v-model:value="cloneFormValue.cloneTemplateId" />
              </n-form-item>
              <n-form-item label="类型" path="permissionType">
                <n-cascader
                  v-model:value="cloneFormValue.permissionType"
                  placeholder="请选择"
                  :options="typeOptions"
                  check-strategy="child"
                  remote
                  :on-load="extendForm.handleLoad"
                />
              </n-form-item>
            </n-form>
            <n-space class="NPbutton">
              <n-button size="large" type="error" @click="onNegativeCloneClick" ghost
                >取消
              </n-button>
              <n-button size="large" type="primary" @click="onPositiveCloneClick" ghost>
                提交
              </n-button>
            </n-space>
          </div>
        </n-card>
      </n-card>
    </n-modal>
    <ExecTemplate ref="execModalRef"></ExecTemplate>
  </div>
</template>

<script setup>
import { FilePlus } from '@vicons/tabler';
import { EditRegular, CopyRegular, PlayCircleRegular } from '@vicons/fa';
import { NSpace, NButton, NIcon } from 'naive-ui';
import { renderTooltip } from '@/assets/render/tooltip';
import { Delete24Regular as Delete } from '@vicons/fluent';
import axios from '@/axios';
import textDialog from '@/assets/utils/dialog';
import { deleteAjax } from '@/assets/CRUD/delete';
import { cloneTemplate } from '@/api/post';
import { storage } from '@/assets/utils/storageUtils';
import extendForm from '@/views/versionManagement/product/modules/createForm.js';
import { createTitle } from '@/assets/utils/createTitle';
import ExpandedCardTemplate from '@/components/templateComponents/ExpandedCardTemplate.vue';
import { Socket } from '@/socket.js';
import settings from '@/assets/config/settings.js';
import { workspace } from '@/assets/config/menu.js';

const templateTableLoading = ref(false);
const templateTableData = ref([]);
const templatePagination = ref({
  //   page: 1,
  //   pageCount: 1, //总页数
  //   pageSize: 10, //受控模式下的分页大小
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50],
});
const isEditTemplate = ref(false);
const modalData = ref(null);

const getTableData = () => {
  return new Promise((resolve) => {
    templateTableLoading.value = true;
    axios.get(`/v1/ws/${workspace.value}/template`).then((res) => {
      templateTableLoading.value = false;
      templateTableData.value = res.data;
      templateList.value = res.data.map((item) => ({
        label: item.name,
        value: String(item.id),
      }));
      resolve();
    });
  });
};

const templateTableColumns = [
  {
    type: 'expand',
    renderExpand: (rowData) =>
      h(ExpandedCardTemplate, {
        data: rowData.suite_cases,
      }),
  },
  {
    title: '模板名称',
    key: 'name',
    align: 'left',
  },
  {
    title: '关联里程碑',
    key: 'milestone',
    align: 'center',
  },
  {
    title: '创建人',
    key: 'author',
    align: 'center',
  },
  {
    title: '权限类型',
    key: 'template_type',
    align: 'center',
  },
  {
    title: '权限归属',
    key: 'owner',
    align: 'center',
  },
  {
    title: '操作',
    key: 'operate',
    align: 'center',
    render(row) {
      return h(
        NSpace,
        {
          justify: 'center',
          align: 'center',
        },
        [
          renderTooltip(
            h(
              NButton,
              {
                size: 'small',
                type: 'warning',
                circle: true,
                onClick: () => {
                  showCreateTemplateModal.value = true;
                  isEditTemplate.value = true;
                  modalData.value = row;
                },
              },
              h(NIcon, { size: '20' }, h(EditRegular))
            ),
            '编辑'
          ),
          renderTooltip(
            h(
              NButton,
              {
                size: 'small',
                type: 'error',
                circle: true,
                onClick: () => {
                  textDialog('warning', '警告', '你确定要删除此模板吗?', async () => {
                    await deleteAjax.singleDelete(`/v1/template/${row.id}`, row.id);
                    getTableData();
                  });
                },
              },
              h(NIcon, { size: '20' }, h(Delete))
            ),
            '删除'
          ),
          renderTooltip(
            h(
              NButton,
              {
                size: 'small',
                type: 'info',
                circle: true,
                onClick: () => {
                  showCloneModal.value = true;
                  cloneFormValue.value.cloneTemplateId = String(row.id);
                },
              },
              h(NIcon, { size: '20' }, h(CopyRegular))
            ),
            '克隆'
          ),
          renderTooltip(
            h(
              NButton,
              {
                size: 'small',
                type: 'success',
                circle: true,
                onClick: () => {
                  execModalRef.value.showModal = true;
                  execModalRef.value.renderExecute(row);
                },
              },
              h(NIcon, { size: '20' }, h(PlayCircleRegular))
            ),
            '执行'
          ),
        ]
      );
    },
  },
];
const templateList = ref([]); // 模板列表

// const templateTablePageChange = () => {};
// const templateTablePageSizeChange = () => {};

const showCreateTemplateModal = ref(false);

const createTemplateBtn = () => {
  showCreateTemplateModal.value = true;
};

const onNegativeClick = () => {
  showCreateTemplateModal.value = false;
  isEditTemplate.value = false;
  modalData.value = null;
  getTableData();
};

const filterRule = ref([
  {
    path: 'name',
    name: '模板名称',
    type: 'input',
  },
  {
    path: 'milestone',
    name: '关联里程碑',
    type: 'input',
  },
  {
    path: 'author',
    name: '创建人',
    type: 'input',
  },
  {
    path: 'template_type',
    name: '权限类型',
    type: 'input',
  },
  {
    path: 'owner',
    name: '权限归属',
    type: 'input',
  },
]);

const filterchange = async (filterArray) => {
  await getTableData();
  templateTableData.value = templateTableData.value.filter((item) => {
    return filterArray.every((v) => {
      if (v.value !== null) {
        return item[v.path].includes(v.value);
      }
      return true;
    });
  });
};

const refreshTableData = () => {
  getTableData();
};

const showCloneModal = ref(false);
const cloneForm = ref();
const cloneFormValue = ref({
  cloneTemplateId: undefined,
  permissionType: undefined,
});
const cloneFormRule = {
  cloneTemplateId: {
    trigger: ['input', 'blur'],
    message: '请选择要克隆的模板',
    validator() {
      if (cloneFormValue.value.cloneTemplateId) {
        return true;
      }
      return false;
    },
  },
  permissionType: {
    trigger: ['input', 'blur'],
    message: '请选择类型',
    validator() {
      if (cloneFormValue.value.permissionType) {
        return true;
      }
      return false;
    },
  },
};

// 类型
const typeOptions = ref([
  //   { label: '公共', value: 'public', isLeaf: true },
  { label: '组织', value: 'org', isLeaf: true },
  { label: '团队', value: 'group', isLeaf: false },
  { label: '个人', value: 'person', isLeaf: true },
]);

// 取消克隆
const onNegativeCloneClick = () => {
  showCloneModal.value = false;
  cloneFormValue.value = {};
};

// 提交克隆
const onPositiveCloneClick = () => {
  return new Promise((resolve, reject) => {
    cloneForm.value?.validate((error) => {
      if (!error) {
        cloneTemplate({
          permission_type: cloneFormValue.value.permissionType.split('-')[0],
          creator_id: storage.getValue('user_id'),
          org_id: storage.getValue('loginOrgId'),
          group_id: Number(cloneFormValue.value.permissionType.split('-')[1]),
          id: Number(cloneFormValue.value.cloneTemplateId),
        })
          .then(() => {
            showCloneModal.value = false;
            cloneFormValue.value = {};
            getTableData();
            resolve();
          })
          .catch((err) => reject(err));
      } else {
        reject(Error('error'));
      }
    });
  });
};

const execModalRef = ref(null);

const templateSocket = new Socket(
  `${settings.websocketProtocol}://${settings.serverPath}/template`
);
templateSocket.connect();

onMounted(() => {
  getTableData();

  templateSocket.listen('update', () => {
    getTableData();
  });
});

onUnmounted(() => {
  templateSocket.disconnect();
});
</script>

<style scoped lang="less">
.containerWrap {
  padding: 20px;
  display: flex;
  flex-direction: column;

  .titleWrap {
    margin-bottom: 15px;
    display: flex;
    justify-content: space-between;

    .menuWrap {
      display: flex;
      align-items: center;

      .filterBtn {
        margin-right: 20px;
      }
    }
  }
}
</style>
