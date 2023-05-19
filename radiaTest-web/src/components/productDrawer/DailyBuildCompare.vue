<template>
  <n-modal v-model:show="showModal" @afterEnter="modalEnter">
    <n-card
      :title="createTitle('与每日构建比对结果')"
      size="large"
      :bordered="false"
      :segmented="{
        content: true
      }"
      style="width: 1200px"
    >
      <n-tabs class="repo-tab" animated type="line" v-model:value="repoPath" @update:value="changeRepoPath">
        <n-tab name="everything"> everything </n-tab>
        <n-tab name="EPOL"> EPOL </n-tab>
        <template #suffix> <create-button title="新增比对" @click="showAddCompareModalCb" /> </template>
      </n-tabs>
      <n-data-table
        remote
        class="tableClass"
        :loading="dailyBuildCompareResultLoading"
        :columns="dailyBuildCompareResultColumns"
        :data="dailyBuildCompareResultData"
        :pagination="dailyBuildCompareResultPagination"
        @update:page="dailyBuildCompareResultPageChange"
        @update:pageSize="dailyBuildCompareResultPageSizeChange"
      />
    </n-card>
  </n-modal>
  <n-modal v-model:show="showAddCompareModal">
    <n-card
      :title="createTitle('新增比对')"
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
            <n-select
              v-model:value="formValue.daily_name"
              placeholder="请选择每日构建名称"
              :options="dailyBuildOptions"
              filterable
              clearable
            />
          </n-form-item-gi>
          <n-form-item-gi :span="24" label="Repo目录" path="repo_path">
            <n-select v-model:value="formValue.repo_path" placeholder="请选择repo目录" :options="repoOptions" />
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
import { Delete24Regular, ArrowDownload16Regular } from '@vicons/fluent';
import { getDailyBuildCompare, getDailyBuild } from '@/api/get';
import { createDailyBuildCompare } from '@/api/post';
import { deleteDailyBuildCompare } from '@/api/delete';
import axios from '@/axios';

const props = defineProps(['roundCurId']);
const { roundCurId } = toRefs(props);
const showModal = ref(false);
const dailyBuildCompareResultData = ref([]);
const dailyBuildCompareResultLoading = ref(false);
const repoPath = ref('everything');
const dailyBuildCompareResultColumns = ref([
  {
    key: 'daily_name',
    title: '比对名称'
  },
  {
    key: 'file_name',
    title: '比对结果'
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
                type: 'default',
                circle: true,
                onClick: (e) => {
                  e.stopPropagation();
                  e.preventDefault();
                  axios
                    .downLoad(`/v1/qualityboard/daily-build/with/round/${roundCurId.value}/pkg-compare-result-export`, {
                      compare_name: row.daily_name
                    })
                    .then((res) => {
                      let blob = new Blob([res], { type: 'application/vnd.ms-excel' });
                      let url = URL.createObjectURL(blob);
                      let alink = document.createElement('a');
                      document.body.appendChild(alink);
                      alink.download = row.file_name;
                      alink.target = '_blank';
                      alink.href = url;
                      alink.click();
                      alink.remove();
                      URL.revokeObjectURL(url);
                    });
                }
              },
              h(NIcon, { size: '20' }, h(ArrowDownload16Regular))
            ),
            '下载'
          ),
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
                  textDialog('warning', '警告', '确认删除每日构建比对结果？', () => {
                    deleteDailyBuildCompareResultCb(row);
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
const dailyBuildCompareResultPagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1, // 总页数
  itemCount: 1, // 总条数
  showSizePicker: true,
  pageSizes: [10, 20, 50, 100]
});

const getDailyBuildCompareResultData = () => {
  dailyBuildCompareResultLoading.value = true;
  dailyBuildCompareResultData.value = [];
  getDailyBuildCompare(roundCurId.value, {
    repo_path: repoPath.value,
    page_num: dailyBuildCompareResultPagination.value.page,
    page_size: dailyBuildCompareResultPagination.value.pageSize
  }).then((res) => {
    dailyBuildCompareResultLoading.value = false;
    dailyBuildCompareResultData.value = res.data?.items;
    dailyBuildCompareResultPagination.value.page = res.data.current_page;
    dailyBuildCompareResultPagination.value.pageCount = res.data.pages;
    dailyBuildCompareResultPagination.value.itemCount = res.data.total;
  });
};

const dailyBuildCompareResultPageChange = (page) => {
  dailyBuildCompareResultPagination.value.page = page;
  getDailyBuildCompareResultData();
};

const dailyBuildCompareResultPageSizeChange = (pageSize) => {
  dailyBuildCompareResultPagination.value.page = 1;
  dailyBuildCompareResultPagination.value.pageSize = pageSize;
  getDailyBuildCompareResultData();
};

const changeRepoPath = (value) => {
  repoPath.value = value;
  dailyBuildCompareResultPagination.value.page = 1;
  getDailyBuildCompareResultData();
};

const setDailyBuildOptions = () => {
  getDailyBuild({ paged: false }).then((res) => {
    dailyBuildOptions.value = res.data.map((item) => {
      return {
        label: item.daily_name,
        value: item.daily_name
      };
    });
  });
};

// 弹框显示回调
const modalEnter = () => {
  dailyBuildCompareResultPagination.value.page = 1;
  getDailyBuildCompareResultData();
  setDailyBuildOptions();
};

const deleteDailyBuildCompareResultCb = (row) => {
  deleteDailyBuildCompare(roundCurId.value, { compare_name: row.daily_name }).then(() => {
    dailyBuildCompareResultPagination.value.page = 1;
    getDailyBuildCompareResultData();
  });
};

const showAddCompareModal = ref(false);
const showAddCompareModalCb = () => {
  showAddCompareModal.value = true;
};
const repoOptions = [
  {
    label: 'everything',
    value: 'everything'
  },
  {
    label: 'EPOL',
    value: 'EPOL'
  }
];
const dailyBuildOptions = ref([]);
const formRef = ref(null);
const formValue = ref({
  daily_name: null,
  repo_path: null
});
const rules = {
  daily_name: {
    required: true,
    message: '每日构建名称不可为空',
    trigger: ['blur', 'select']
  },
  repo_path: {
    required: true,
    message: 'repo目录不可为空',
    trigger: ['blur', 'select']
  }
};

const clean = () => {
  showAddCompareModal.value = false;
  formValue.value = {
    daily_name: null,
    repo_path: null
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
      createDailyBuildCompare(roundCurId.value, {
        daily_name: formValue.value.daily_name,
        repo_path: formValue.value.repo_path
      }).then(() => {
        clean();
        dailyBuildCompareResultPagination.value.page = 1;
        getDailyBuildCompareResultData();
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
