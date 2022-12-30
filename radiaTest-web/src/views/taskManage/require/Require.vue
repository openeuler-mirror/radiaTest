<template>
  <n-grid :cols="24">
    <n-gi :span="17">
      <div class="body-container">
        <div class="body-header">
          <p class="body-header-item">
            <create-button title="发布新需求" @click="() => createModal.show()" />
          </p>
          <p class="body-header-item">
            <filterButton
              style="margin: 0 20px 0 20px"
              :filterRule="filterRule"
              @filterchange="filterchange"
            ></filterButton>
          </p>
        </div>
        <div class="hovered-card body-card">
          <div class="body-content">
            <require-list :data="requireListData" />
          </div>
          <div class="body-footer">
            <n-pagination
              v-model:page="page"
              v-model:page-size="pageSize"
              :page-count="pageCount"
              show-size-picker
              :page-sizes="[10, 20, 30, 50]"
              @update:page="handlePageChange"
              @update:page-size="handlePageSizeChange"
            />
          </div>
        </div>
      </div>
    </n-gi>
    <n-gi :span="7">
      <div style="padding: 20px 40px 20px 40px">
        <n-card
          class="hovered-card"
          :content-style="{
            padding: '0'
          }"
        >
          <n-tabs animated type="line" justify-content="space-evenly">
            <n-tab
              name="person"
              @click="
                () => {
                  rankType = 'person';
                }
              "
              >个人</n-tab
            >
            <n-tab
              name="group"
              @click="
                () => {
                  rankType = 'group';
                }
              "
              >团队</n-tab
            >
          </n-tabs>
          <div class="all-rank-container">
            <n-spin :show="loading">
              <div class="rank-item all-rank" v-for="(item, index) in rankList" :key="index">
                <p class="rank-item-header">
                  <n-gradient-text class="rank-item-header-number"> {{ item.rank }}. </n-gradient-text>
                  <n-avatar
                    circle
                    :fallback-src="handleFallbackSrc(item)"
                    :size="24"
                    :src="item.avatar_url"
                    style="margin-right: 10px"
                  />
                  <span class="rank-item-header-name">{{ item.gitee_name ? item.gitee_name : item.name }}</span>
                </p>
                <p class="rank-item-bq">
                  <span class="rank-item-bq-number">{{ item.influence }}</span>
                  <n-icon :size="16">
                    <radio />
                  </n-icon>
                </p>
              </div>
            </n-spin>
          </div>
          <div class="rank-pagination">
            <n-pagination
              v-model:page="rankPage"
              :page-size="rankPageSize"
              :page-count="rankPageCount"
              :simple="true"
              size="small"
              @update:page="handleRankPageChange"
            />
          </div>
          <div class="self-rank rank-item" v-if="rankType === 'person'">
            <p class="rank-item-header">
              <n-text class="rank-item-header-number"> {{ accountRank }}. </n-text>
              <n-avatar
                circle
                :fallback-src="createAvatar(accountName.slice(0, 1))"
                :size="24"
                :src="avatarUrl"
                style="margin-right: 10px"
              />
              <span class="rank-item-header-name">{{ accountName }}</span>
            </p>
            <p class="rank-item-bq">
              <span class="rank-item-bq-number">{{ influenceScore }}</span>
              <n-icon :size="16">
                <radio />
              </n-icon>
            </p>
          </div>
        </n-card>
      </div>
    </n-gi>
  </n-grid>
  <modal-card
    ref="createModal"
    :initY="100"
    :initX="300"
    title="发布新需求"
    @validate="() => formRef.handlePropsButtonClick()"
  >
    <template #form>
      <require-create ref="formRef" @valid="createModal.close()" />
    </template>
  </modal-card>
</template>

<script setup>
import { createAvatar } from '@/assets/utils/createImg';
import CreateButton from '@/components/CRUD/CreateButton';
import filterButton from '@/components/filter/filterButton';
import { Radio } from '@vicons/ionicons5';
import RequireList from './requireList/RequireList';
import RequireCreate from './requireCreate/RequireCreate.vue';
import { getUserAssetRank, getGroupAssetRank, getUserInfo, getRequireList } from '@/api/get';
import { storage } from '@/assets/utils/storageUtils';
import settings from '@/assets/config/settings';
import { Socket } from '@/socket';

const requirementSocket = new Socket(`${settings.websocketProtocol}://${settings.serverPath}/requirement`);
requirementSocket.connect();
const rankSocket = new Socket(`${settings.websocketProtocol}://${settings.serverPath}/rank`);
rankSocket.connect();

const influenceScore = ref(0);
const accountRank = ref(null);
const accountName = ref('');
const avatarUrl = ref(null);

const loading = ref(false);
const createModal = ref(null);
const formRef = ref(null);

const filterParams = ref({
  status: null,
  title: null,
  remark: null,
  description: null,
  payload: null,
  payload_operator: null,
  period: null,
  period_operator: null,
  influence_require: null,
  behavior_require: null,
  total_reward: null
});

const page = ref(1);
const pageSize = ref(10);
const pageCount = ref(1);

const rankList = ref([]);

const filterRule = ref([
  {
    path: 'status',
    name: '状态',
    type: 'select',
    options: [
      { label: '可接受', value: 'idle' },
      { label: '已接收', value: 'accepted' },
      { label: '已完成', value: 'validated' }
    ]
  },
  {
    path: 'title',
    name: '标题',
    type: 'input'
  },
  {
    path: 'remark',
    name: '简介',
    type: 'input'
  },
  {
    path: 'description',
    name: '描述',
    type: 'input'
  },
  {
    path: 'payload',
    name: '预计工作量',
    type: 'number',
    condition: true,
    conditionOptions: [
      { label: '=', value: '=' },
      { label: '>', value: '>' },
      { label: '>=', value: '>=' },
      { label: '<', value: '<' },
      { label: '<=', value: '<=' }
    ],
    conditionValue: 'payload_operator'
  },
  {
    path: 'period',
    name: '交付周期',
    type: 'number',
    condition: true,
    conditionOptions: [
      { label: '=', value: '=' },
      { label: '>', value: '>' },
      { label: '>=', value: '>=' },
      { label: '<', value: '<' },
      { label: '<=', value: '<=' }
    ],
    conditionValue: 'period_operator'
  },
  {
    path: 'influence_require',
    name: '影响力门槛',
    type: 'number'
  },
  {
    path: 'behavior_require',
    name: '信誉分门槛',
    type: 'number'
  },
  {
    path: 'total_reward',
    name: '影响力奖励',
    type: 'number'
  }
]);

const filterchange = (filterArray) => {
  filterParams.value = {
    status: null,
    title: null,
    remark: null,
    description: null,
    payload: null,
    payload_operator: null,
    period: null,
    period_operator: null,
    influence_require: null,
    behavior_require: null,
    total_reward: null
  };
  filterArray.forEach((v) => {
    filterParams.value[v.path] = v.value;
  });
  page.value = 1;
  getRequirementData();
};

const rankType = ref('person');
const rankPage = ref(1);
const rankPageCount = ref(1);
const rankPageSize = ref(20);

function getRank(asyncFunc) {
  asyncFunc({ page_num: rankPage.value, page_size: rankPageSize.value }).then((res) => {
    rankList.value = res.data.items;
    rankPage.value = res.data.current_page;
    rankPageCount.value = res.data.pages;
  });
}

const requireListData = ref([]);

function handleRankPageChange() {
  if (rankType.value === 'person') {
    getRank(getUserAssetRank);
  } else {
    getRank(getGroupAssetRank);
  }
}

function getRequirementData() {
  getRequireList({
    page_num: page.value,
    page_size: pageSize.value,
    ...filterParams.value
  }).then((res) => {
    requireListData.value = res.data.items;
    page.value = res.data.current_page;
    pageCount.value = res.data.pages;
  });
}

function handlePageChange(_page) {
  page.value = _page;
  getRequirementData();
}

function handlePageSizeChange(_pageSize) {
  pageSize.value = _pageSize;
  page.value = 1;
  getRequirementData();
}

function handleFallbackSrc(item) {
  if (item.gitee_name) {
    return createAvatar(item.gitee_name.slice(0, 1));
  }
  return null;
}

onMounted(() => {
  getRank(getUserAssetRank);
  getUserInfo(storage.getValue('gitee_id')).then((res) => {
    accountName.value = res.data.gitee_name;
    accountRank.value = res.data.rank;
    avatarUrl.value = res.data.avatar_url;
    influenceScore.value = res.data.influence;
  });
  getRequirementData();
  requirementSocket.listen('update', () => {
    getRequirementData();
  });
  rankSocket.listen('update', () => {
    if (rankType.value === 'person') {
      getRank(getUserAssetRank);
    } else {
      getRank(getGroupAssetRank);
    }
  });
});

watch(rankType, () => {
  handleRankPageChange();
});
</script>

<style scoped lang="less">
.hovered-card {
  border-radius: 20px;
  box-shadow: 0 1px 2px -2px rgba(0, 0, 0, 0.08), 0 3px 6px 0 rgba(0, 0, 0, 0.06), 0 5px 12px 4px rgba(0, 0, 0, 0.04);
}
.intro {
  display: flex;
  justify-content: center;
}
.account-name {
  font-size: 20px;
}
.score {
  justify-content: space-evenly;
}
.score-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  .score-item-number {
    display: flex;
    color: #002fa7;
    font-size: 22px;
    margin-bottom: 0;
    align-items: center;
  }
  .score-item-title {
    margin: 0;
  }
}
.all-rank-container {
  overflow: scroll;
  height: 560px;
}
.rank-item {
  display: flex;
  justify-content: space-between;
  .rank-item-header {
    display: flex;
    align-items: center;
    justify-content: space-evenly;
    margin-left: 20px;
    .rank-item-header-number {
      margin-right: 10px;
      font-size: 16px;
      font-weight: 900;
    }
    .rank-item-header-name {
      font-family: monospace;
      font-size: 16px;
    }
  }
  .rank-item-bq {
    display: flex;
    align-items: center;
    justify-content: space-evenly;
    margin-right: 20px;
    .rank-item-bq-number {
      margin-right: 10px;
      color: #002fa7;
      font-size: 16px;
    }
  }
}
.rank-pagination {
  margin: 10px 0 10px 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.all-rank:hover {
  background-image: linear-gradient(71deg, #4b94d5, transparent);
  box-shadow: 0 1px 2px -2px rgba(0, 0, 0, 0.08), 0 3px 6px 0 rgba(0, 0, 0, 0.06), 0 5px 12px 4px rgba(0, 0, 0, 0.04);
}
.self-rank {
  color: white;
  background-color: #4b94d5;
  border-radius: 0 0 20px 20px;
  .rank-item-header {
    .rank-item-header-number {
      font-size: 16px;
      font-weight: 900;
      color: white;
    }
  }
  .rank-item-bq {
    .rank-item-bq-number {
      color: white;
    }
  }
}
.body-container {
  padding: 20px;
  .body-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    .body-header-item {
      display: flex;
      align-items: center;
    }
  }
  .body-card {
    border-radius: 0 0 20px 20px;
  }
}
.body-content {
  overflow: hidden;
}
.body-footer {
  display: flex;
  align-content: center;
  justify-content: flex-end;
  padding: 10px 40px 10px 10px;
}
</style>
