<template>
  <n-modal v-model:show="showModal" @afterEnter="modalEnter">
    <n-card
      :title="createTitle('每日构建列表')"
      size="large"
      :bordered="false"
      :segmented="{
        content: true
      }"
      style="width: 1200px"
    >
      <create-button title="新建每日构建" @click="showCreateDailyBuildModalCb" />
      <n-data-table
        remote
        class="tableClass"
        :loading="dailyBuildTableLoading"
        :columns="dailyBuildTableColumns"
        :data="dailyBuildTableData"
        :pagination="dailyBuildTablePagination"
        @update:page="dailyBuildTablePageChange"
        @update:pageSize="dailyBuildTablePageSizeChange"
      />
    </n-card>
  </n-modal>
  <n-modal v-model:show="showCreateDailyBuildModal">
    <n-card
      :title="createTitle('新建每日构建')"
      size="large"
      :bordered="false"
      :segmented="{
        content: true
      }"
      style="width: 800px"
    >
      <n-form inline :label-width="80" :model="formValue" :rules="rules" size="medium" ref="formRef">
        <n-grid :cols="24">
          <n-form-item-gi :span="24" label="每日构建名称" path="daily_name">
            <n-input v-model:value="formValue.daily_name" placeholder="请输入每日构建名称" />
          </n-form-item-gi>
          <n-form-item-gi :span="24" label="repo地址" path="repo_url">
            <n-input v-model:value="formValue.repo_url" placeholder="请输入repo地址" />
          </n-form-item-gi>
        </n-grid>
      </n-form>
      <n-space>
        <n-button size="large" type="error" @click="onNegativeClick" ghost>取消 </n-button>
        <n-button size="large" type="primary" @click="onPositiveClick" ghost> 提交 </n-button>
      </n-space>
    </n-card>
  </n-modal>
</template>

<script setup>
import { createTitle } from '@/assets/utils/createTitle';
import { NButton, NIcon, NSpace } from 'naive-ui';
import { renderTooltip } from '@/assets/render/tooltip';
import textDialog from '@/assets/utils/dialog';
import { Delete24Regular } from '@vicons/fluent';
import { getDailyBuild } from '@/api/get';
import { createDailyBuild } from '@/api/post';
import { deleteDailyBuild } from '@/api/delete';

const showModal = ref(false);
const dailyBuildTableData = ref([]);
const dailyBuildTableLoading = ref(false);
const dailyBuildTableColumns = ref([
  {
    key: 'daily_name',
    title: '每日构建名称'
  },
  {
    key: 'repo_url',
    title: 'repo地址'
  },
  {
    title: '操作',
    align: 'center',
    render(row) {
      return h(
        NSpace,
        {
          justify: 'center',
          align: 'center'
        },
        [
          renderTooltip(
            h(
              NButton,
              {
                size: 'medium',
                type: 'error',
                circle: true,
                onClick: (e) => {
                  e.stopPropagation();
                  e.preventDefault();
                  textDialog('warning', '警告', '确认删除每日构建？', () => {
                    deleteDailyBuildCb(row);
                  });
                }
              },
              h(NIcon, { size: '20' }, h(Delete24Regular))
            ),
            '删除'
          )
        ]
      );
    }
  }
]);
const dailyBuildTablePagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1, // 总页数
  itemCount: 1, // 总条数
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100]
});

const getDailyBuildData = () => {
  dailyBuildTableLoading.value = true;
  dailyBuildTableData.value = [];
  getDailyBuild({
    page_num: dailyBuildTablePagination.value.page,
    page_size: dailyBuildTablePagination.value.pageSize
  }).then((res) => {
    dailyBuildTableLoading.value = false;
    dailyBuildTableData.value = res.data.items;
    dailyBuildTablePagination.value.page = res.data.current_page;
    dailyBuildTablePagination.value.pageCount = res.data.pages;
    dailyBuildTablePagination.value.itemCount = res.data.total;
  });
};

const dailyBuildTablePageChange = (page) => {
  dailyBuildTablePagination.value.page = page;
  getDailyBuildData();
};

const dailyBuildTablePageSizeChange = (pageSize) => {
  dailyBuildTablePagination.value.page = 1;
  dailyBuildTablePagination.value.pageSize = pageSize;
  getDailyBuildData();
};

// 弹框显示回调
const modalEnter = () => {
  dailyBuildTablePagination.value.page = 1;
  getDailyBuildData();
};

const deleteDailyBuildCb = (row) => {
  deleteDailyBuild({ daily_name: row.daily_name }).then(() => {
    dailyBuildTablePagination.value.page = 1;
    getDailyBuildData();
  });
};

const showCreateDailyBuildModal = ref(false);
const showCreateDailyBuildModalCb = () => {
  showCreateDailyBuildModal.value = true;
};

const formRef = ref(null);
const formValue = ref({
  daily_name: null,
  repo_url: null
});
const rules = {
  daily_name: {
    required: true,
    message: '每日构建名称不可为空',
    trigger: ['blur', 'input']
  },
  repo_url: {
    required: true,
    message: 'repo地址不可为空',
    trigger: ['blur', 'input']
  }
};

const clean = () => {
  showCreateDailyBuildModal.value = false;
  formValue.value = {
    daily_name: null,
    repo_url: null
  };
};

const onNegativeClick = () => {
  clean();
};

const onPositiveClick = () => {
  formRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请检查输入合法性');
    } else {
      createDailyBuild({ daily_name: formValue.value.daily_name, repo_url: formValue.value.repo_url }).then(() => {
        clean();
        dailyBuildTablePagination.value.page = 1;
        getDailyBuildData();
      });
    }
  });
};

defineExpose({
  showModal
});
</script>

<style scoped lang="less">
.tableClass {
  margin-top: 20px;
}
</style>
