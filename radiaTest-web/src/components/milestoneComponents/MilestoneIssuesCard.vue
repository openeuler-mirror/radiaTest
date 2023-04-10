<template>
  <n-card hoverable id="issueCard">
    <n-grid :cols="24" :x-gap="12">
      <n-gi :span="15">
        <h3>{{ total }} issues in total</h3>
      </n-gi>
      <n-gi :span="6"></n-gi>
      <n-gi :span="3">
        <n-select
          v-model:value="stateType"
          :options="issueTypeOpts"
          @update:value="changeState"
          round
          placeholder="请选择"
        />
      </n-gi>
    </n-grid>
    <n-data-table
      ref="table"
      size="small"
      :bordered="false"
      :loading="loading"
      :columns="columns"
      :data="rawData"
      :row-props="rowProps"
      :row-key="(row) => row.id"
      :pagination="pagination"
      remote
      @update:page="changePage"
      @update:page-size="changePageSize"
    />
  </n-card>
  <n-drawer v-model:show="active" :width="800" placement="right" :trap-focus="false">
    <n-drawer-content :title="details?.title">
      <div class="drawer-header">
        <p class="item status" :style="{ backgroundColor: details?.issue_state?.color }">
          <IssueState
            :size="issueStateDict[details?.issue_state?.title]?.size || 24"
            color="#fff"
            :tip="details?.issue_state?.title"
          >
            <n-icon :component="issueStateDict[details?.issue_state?.title]?.icon || SyncCircle" />
          </IssueState>
          <span>{{ details?.issue_state?.title }}</span>
        </p>
        <span class="item btn">
          <n-tag
            :color="{
              color: 'rgba(245,246,248,1)',
              textColor: 'rgba(150,161,175,1)'
            }"
            :bordered="false"
          >
            {{ `#${details?.id}` }}
          </n-tag>
        </span>
        <span class="item">
          <n-tag
            v-if="details?.priority === 1"
            :color="{
              textColor: 'rgba(72,168,68,1)',
              borderColor: 'rgba(72,168,68,1)'
            }"
          >
            可选
          </n-tag>
          <n-tag
            v-else-if="details?.priority === 2"
            :color="{
              textColor: 'rgba(0,138,255,1)',
              borderColor: 'rgba(0,138,255,1)'
            }"
          >
            次要
          </n-tag>
          <n-tag
            v-else-if="details?.priority === 3"
            :color="{
              textColor: 'rgba(255,143,0,1)',
              borderColor: 'rgba(255,143,0,1)'
            }"
          >
            主要
          </n-tag>
          <n-tag
            v-else
            :color="{
              textColor: 'rgba(239,0,22,1)',
              borderColor: 'rgba(239,0,22,1)'
            }"
          >
            严重
          </n-tag>
        </span>
        <span class="item">
          <n-icon class="label">
            <User />
          </n-icon>
          <userInfo :userInfo="details?.creatorInfo || {}"> </userInfo>
        </span>
        <span class="item"> 创建于 {{ formatTime(details?.created_at, 'yyyy-MM-dd hh:mm:ss') }} </span>
      </div>
      <div class="content" v-html="details?.description_html"></div>
      <template #footer>
        <n-button @click="openIssuePage" icon-placement="right">
          前往Issue
          <template #icon>
            <n-icon>
              <ArrowForwardOutline />
            </n-icon>
          </template>
        </n-button>
      </template>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup>
import { SyncCircle, ArrowForwardOutline } from '@vicons/ionicons5';
import { User } from '@vicons/tabler';
import issuesColumns, { issueStateDict } from '@/views/versionManagement/milestone/modules/issueTableColumns.js';
import IssueState from '@/components/public/IssueState.vue';
import userInfo from '@/components/user/userInfo.vue';
import { formatTime } from '@/assets/utils/dateFormatUtils';
import { getIssueType, getIssue, getRoundIssue, getIssueDetails } from '@/api/get';
import _ from 'lodash';

const props = defineProps({
  milestoneId: Number,
  cardType: String
});
const { milestoneId, cardType } = toRefs(props);
const details = ref({});
const rawData = ref([]);
const stateType = ref(null);
const issueTypeOpts = ref([]);
const loading = ref(false);
const columns = ref([]);
const total = ref(0);
const active = ref(false);
const pagination = ref({
  pageSize: 10,
  page: 1,
  pageCount: 1,
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
});

const getData = () => {
  loading.value = true;
  if (cardType.value === 'round') {
    getRoundIssue(milestoneId.value, {
      page: pagination.value.page,
      per_page: pagination.value.pageSize,
      issue_type_id: stateType.value
    })
      .then((res) => {
        const resData = JSON.parse(res.data);
        resData.data.forEach((item) => {
          item.milestoneTitle = item.milestone?.title || '无';
        });
        rawData.value = resData.data;
        total.value = resData.total_count;
        pagination.value.pageCount = Math.ceil(Number(total.value) / pagination.value.pageSize) || 1;
      })
      .finally(() => {
        loading.value = false;
      });
  } else {
    getIssue({
      page: pagination.value.page,
      per_page: pagination.value.pageSize,
      milestone_id: milestoneId.value,
      issue_type_id: stateType.value
    })
      .then((res) => {
        const resData = JSON.parse(res.data);
        rawData.value = resData.data;
        total.value = resData.total_count;
        pagination.value.pageCount = Math.ceil(Number(total.value) / pagination.value.pageSize) || 1;
      })
      .finally(() => {
        loading.value = false;
      });
  }
};
const changeState = (state) => {
  stateType.value = state;
  getData();
};
const changePage = (page) => {
  pagination.value.page = page;
  getData();
};
const changePageSize = (pageSize) => {
  pagination.value.page = 1;
  pagination.value.pageSize = pageSize;
  getData();
};
const openIssuePage = () => {
  window.open(details.value.issue_url);
};
const getIssueStateType = () => {
  getIssueType().then((res) => {
    issueTypeOpts.value = res.data.map((item) => ({ label: item.title, value: String(item.id) }));
    const defect = issueTypeOpts.value.find((item) => item.label === '缺陷');
    if (defect) {
      stateType.value = defect.value;
      getData();
    } else {
      window.$message?.info('当前组织企业仓的任务类型不存在"缺陷",请手动选择要查询的任务类型');
    }
  });
};
const rowProps = (row) => {
  return {
    style: {
      cursor: 'pointer'
    },
    onClick: () => {
      active.value = true;
      getIssueDetails(row.id).then((res) => {
        details.value = JSON.parse(res.data);
        details.value.creatorInfo = {
          avatar_url: JSON.parse(res.data).author?.avatar_url,
          user_name: JSON.parse(res.data).author?.username,
          phone: JSON.parse(res.data).author?.phone,
          cla_email: JSON.parse(res.data).author?.email
        };
      });
    }
  };
};

onMounted(() => {
  if (cardType.value === 'round') {
    columns.value = _.cloneDeep(issuesColumns);
    columns.value.splice(2, 0, {
      title: '里程碑',
      key: 'milestoneTitle',
      className: 'cols'
    });
  } else {
    columns.value = issuesColumns;
  }
  getIssueStateType();
});
</script>

<style scoped lang="less">
.issueState {
  width: 5%;
}
.issueNumber {
  width: 5%;
}
.issueTitle {
  width: 42%;
}
.drawer-header {
  display: flex;
  align-items: center;
  .item {
    margin: 0 5px;
  }
  .btn {
    background-color: #ccc;
  }
}
.status {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  padding: 0 5px;
}
</style>
