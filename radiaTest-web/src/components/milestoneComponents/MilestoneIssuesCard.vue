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
    />
  </n-card>
  <n-drawer
    v-model:show="active"
    :width="800"
    placement="right"
    :trap-focus="false"
  >
    <n-drawer-content :title="details?.title">
      <div class="drawer-header">
        <p
          class="item status"
          :style="{ backgroundColor: details?.issue_state?.color }"
        >
          <IssueState
            :size="issueStateDict[details?.issue_state?.title]?.size || 24"
            color="#fff"
            :tip="details?.issue_state?.title"
          >
            <n-icon
              :component="
                issueStateDict[details?.issue_state?.title]?.icon || SyncCircle
              "
            />
          </IssueState>
          <span>{{ details?.issue_state?.title }}</span>
        </p>
        <span class="item btn">
          <n-tag
            :color="{
              color: 'rgba(245,246,248,1)',
              textColor: 'rgba(150,161,175,1)',
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
              borderColor: 'rgba(72,168,68,1)',
            }"
          >
            可选
          </n-tag>
          <n-tag
            v-else-if="details?.priority === 2"
            :color="{
              textColor: 'rgba(0,138,255,1)',
              borderColor: 'rgba(0,138,255,1)',
            }"
          >
            次要
          </n-tag>
          <n-tag
            v-else-if="details?.priority === 3"
            :color="{
              textColor: 'rgba(255,143,0,1)',
              borderColor: 'rgba(255,143,0,1)',
            }"
          >
            主要
          </n-tag>
          <n-tag
            v-else
            :color="{
              textColor: 'rgba(239,0,22,1)',
              borderColor: 'rgba(239,0,22,1)',
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
        <span class="item">
          创建于 {{ formatTime(details?.created_at, 'yyyy-MM-dd hh:mm:ss') }}
        </span>
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

<script>
import { ref, defineComponent } from 'vue';
import issuesColumns, { issueStateDict } from '@/views/milestone/modules/issueTableColumns.js';
import {
  SyncCircle,
  ArrowForwardOutline
} from '@vicons/ionicons5';
// import milestoneIssuesAjax from '@/views/milestone/modules/milestoneIssuesAjax.js';
import { getIssueType, getIssue, getIssueDetails } from '@/api/get';
import IssueState from '@/components/public/IssueState.vue';
import { User } from '@vicons/tabler';
import userInfo from '@/components/user/userInfo.vue';
import { formatTime } from '@/assets/utils/dateFormatUtils';

export default defineComponent({
  components: {
    IssueState,
    User,
    ArrowForwardOutline,
    userInfo
  },
  props: {
    form: Object,
  },
  mounted() {
    this.getIssueStateType();
  },
  methods: {
    openIssuePage() {
      window.open(this.details.issue_url);
    },
    searchIssue() {
      this.changePage(this.pagination.page);
    },
    changeState(state) {
      this.stateType = state;
      this.getData();
    },
    changePage(page) {
      this.pagination.page = page;
      this.getData();
    },
    getData() {
      this.loading = true;
      getIssue({
        page: this.pagination.page,
        per_page: this.pagination.pageSize,
        milestone_id: this.form.id,
        issue_type_id: this.stateType
      })
        .then((res) => {
          const resData = JSON.parse(res.data);
          this.rawData = resData.data;
          this.total = resData.total_count;
          this.loading = false;
          this.pagination.pageCount = Math.ceil(Number(this.total) / this.pagination.pageSize) || 1;
        })
        .catch((err) => {
          if (err.data.validation_error) {
            window.$message.error(err.data.validation_error.body_params[0].msg);
          } else {
            window.$message.error('发生未知错误，获取数据失败');
          }
          this.loading = false;
        });
    },
    getIssueStateType() {
      getIssueType().then(res => {
        this.issueTypeOpts = JSON.parse(res.data).data.map(item => ({ label: item.title, value: String(item.id) }));
        const defect = this.issueTypeOpts.find(item => item.label === '缺陷');
        if (defect) {
          this.stateType = defect.value;
          this.getData();
        } else {
          window.$message?.info('当前组织企业仓的任务类型不存在"缺陷",请手动选择要查询的任务类型');
        }
      });
    },
    rowProps(row) {
      return {
        style: {
          cursor: 'pointer',
        },
        onClick: () => {
          this.active = true;
          getIssueDetails(row.id).then(res => {
            this.details = JSON.parse(res.data);
            this.details.creatorInfo = {
              avatar_url: JSON.parse(res.data).author?.avatar_url,
              gitee_name: JSON.parse(res.data).author?.username,
              phone: JSON.parse(res.data).author?.phone,
              cla_email: JSON.parse(res.data).author?.email
            };
            console.log(this.details);
          });
        },
      };
    },
  },
  data() {
    return {
      details: {}
    };
  },
  setup() {
    const rawData = ref([]);
    const issueTypeOpts = ref([]);
    const loading = ref(false);
    const columns = issuesColumns;
    const total = ref(0);
    const title = ref(null);
    const assignee = ref(null);
    const active = ref(false);
    const pagination = ref({
      pageSize: 10,
      page: 1,
      pageCount: 1
    });

    return {
      SyncCircle,
      issueStateDict,
      active,
      formatTime,
      stateType: ref(null),
      rawData,
      loading,
      columns,
      issueTypeOpts,
      pagination,
      total,
      title,
      assignee,
    };
  },
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
