<template>
  <div class="workspaces-container">
    <n-layout
        :content-style="{
        padding: '24px',
        backgroundColor: '#f5f5f5'
      }"
        embedded
    >
      <div class="welcome-warp">
        <h2>Hi，欢迎使用开源测试管理平台radiaTest！</h2>
        <p>radiaTest提供一站式测试资产管理、测试服务编排调用、以及跨团队版本级测试协作能力。</p>
        <div class="detail-wrap">
          <n-icon color="#429cee">
            <Check></Check>
          </n-icon>
          <div class="text">版本级质量看板，使能社区版本测试可跟踪可追溯</div>
        </div>
        <div class="detail-wrap">
          <n-icon color="#429cee">
            <Check></Check>
          </n-icon>
          <div class="text">多元化资源池，无障碍对接各类资源管理系统和组网</div>
        </div>
        <div class="detail-wrap">
          <n-icon color="#429cee">
            <Check></Check>
          </n-icon>
          <div class="text">文本用例统一看管，为社区文本用例的开发与评审提供基座</div>
        </div>
        <div class="detail-wrap">
          <n-icon color="#429cee">
            <Check></Check>
          </n-icon>
          <div class="text">多元化测试服务编排，满足社区差异化测试能力需求，灵活选用</div>
        </div>
        <div class="detail-wrap">
          <n-icon color="#429cee">
            <Check></Check>
          </n-icon>
          <div class="text">任务管理管理能力，实现测试活动全流程承载</div>
        </div>
        <div class="image-box">
          <n-image :src="titleImage" height="250" preview-disabled width="350"/>
        </div>
        <div class="stat-box">
          <n-statistic label="当前组织已有" tabular-nums>
            <n-number-animation ref="groupStat" :from="0" :to="totalGroupNum"/>
            <template #suffix> 个团队接入</template>
          </n-statistic>
          <n-statistic label="当前组织已有" tabular-nums>
            <n-number-animation ref="userStat" :from="0" :to="totalUserNum"/>
            <template #suffix> 位用户注册</template>
          </n-statistic>
        </div>
      </div>
      <n-grid :cols="12" style="margin-top: 20px" x-gap="24">
        <n-gi :span="10">
          <div class="workspaces-wrap">
            <div class="workspaces-title">Workspaces</div>
            <n-collapse :default-expanded-names="['publicWorkspaces', 'groupWorkspaces']" class="workspaces-content">
              <n-collapse-item name="publicWorkspaces" title="公共workspaces">
                <n-grid :cols="2" x-gap="24">
                  <n-gi :span="1">
                    <div class="publicworkspaces-wrap" @click="clickDefaultWorkspace">
                      <div>
                        <n-avatar :size="100" :src="orgAvatarSrc"></n-avatar>
                      </div>
                      <div class="detail-box">
                        <h3>默认workspace</h3>
                        <p>
                          当前组织下的默认视图，用户可以查看组织、所属团队以及个人的所有权限内事务（包括Job、机器、任务、策略、报告、用例等）
                        </p>
                      </div>
                    </div>
                  </n-gi>
                  <n-gi :span="1">
                    <div class="publicworkspaces-wrap " @click="clickVersionWorkspace">
                      <div>
                        <n-avatar :size="100" :src="orgAvatarSrc"></n-avatar>
                      </div>
                      <div class="detail-box">
                        <h3>版本workspace</h3>
                        <p>
                          当前组织下的版本级视图，主要围绕当前待发布版本的测试活动展开，全局展示当前版本迭代阶段与质量状况
                        </p>
                      </div>
                    </div>
                  </n-gi>
                </n-grid>
              </n-collapse-item>
              <n-collapse-item name="groupWorkspaces" title="团队workspaces">
                <n-tabs type="line">
                  <n-tab name="all"> 全部</n-tab>
                  <n-tab :disabled="true" name="myJoin"> 我加入的</n-tab>
                  <n-tab :disabled="true" name="myCreate"> 我创建的</n-tab>
                </n-tabs>
                <template #header-extra>
                  <n-input
                      v-model:value="searchGroupValue"
                      clearable
                      placeholder="请输入团队名称"
                      @change="searchValueChange"
                      @click.stop.prevent
                  />
                </template>
                <div class="group-workspaces-wrap">
                  <div
                      v-for="(groupItem, groupIndex) in groupList"
                      :key="groupIndex"
                      class="group-workspace"
                      @click="clickGroupWorkspace(groupItem)"
                  >
                    <div class="group-workspace-content">
                      <div class="detail">
                        <div class="image-wrap">
                          <n-image
                              :fallback-src="createAvatar(groupItem.groupName.slice(0, 1), 100)"
                              :src="groupItem.groupAvatarUrl"
                              width="50"
                          />
                        </div>
                        <div class="name-user">
                          <div class="name">{{ groupItem.groupName }}</div>
                          <div class="user-wrap">
                            <AvatarGroup :max="3" :options="groupItem.AvatarList" :size="30"/>
                          </div>
                        </div>
                      </div>
                      <span class="description">{{ groupItem.description }}</span>
                      <div v-if="!groupItem.isAllowed" class="lock-icon">
                        <n-tooltip trigger="hover">
                          <template #trigger>
                            <n-icon :size="16">
                              <Lock/>
                            </n-icon>
                          </template>
                          不属于该用户组成员，无法进入此workspace
                        </n-tooltip>
                      </div>
                    </div>
                  </div>
                </div>
                <n-pagination
                    v-model:page="groupPage"
                    v-model:page-size="groupPageSize"
                    :page-count="groupTotal"
                    :page-sizes="[12, 24, 48, 100]"
                    class="pagination-wrap"
                    show-size-picker
                    @update:page="groupPageChange"
                    @update:page-size="groupPageSizeChange"
                />
              </n-collapse-item>
            </n-collapse>
          </div>
        </n-gi>
        <n-gi :span="2">
          <div class="document-wrap">
            <div class="document-title">
              <div class="document-text">公告</div>
              <div class="view-all">查看全部</div>
            </div>
            <div v-for="item in noticeList" :key="item.id" class="hover">
              <n-tag size="small" style="margin-right: 0.5rem;margin-bottom: 0.5rem" type="error">
                {{ item.tag }}
              </n-tag>
              <router-link :to="`/home/notice/${item.title}`">{{ item.title }}</router-link>
            </div>
            <div class="document-content-wrap">
              <div class="document-content">
                <div class="content-type document-first">发布</div>
                <div class="content-text">
                </div>
              </div>
            </div>
          </div>
          <div class="document-wrap help-document">
            <div class="document-title">
              <div class="document-text">帮助文档</div>
              <div class="view-all">查看全部</div>
            </div>
            <div v-for="item in docList" :key="item.id" class="hover">
              <n-tag size="small" style="margin-right: 0.5rem;margin-bottom: 0.5rem;" type="info">
                {{ item.tag }}
              </n-tag>
              <router-link :to="`/home/doc/${item.title}`">{{ item.title }}</router-link>
            </div>
            <div class="document-content-wrap">
              <div class="document-content">
                <div class="content-type document-first">文档</div>
                <div class="content-text"></div>
              </div>
            </div>
          </div>
          <n-card
              :content-style="{
              padding: '0'
            }"
              class="hovered-card rank-wrap"
          >
            <n-tabs animated justify-content="space-evenly" type="line">
              <n-tab
                  name="person"
                  @click="
                  () => {
                    rankType = 'person';
                  }
                "
              >个人积分
              </n-tab
              >
              <n-tab
                  name="group"
                  @click="
                  () => {
                    rankType = 'group';
                  }
                "
              >团队积分
              </n-tab
              >
            </n-tabs>
            <div class="all-rank-container">
              <n-spin :show="loading">
                <div v-for="(item, index) in rankList" :key="index" class="rank-item all-rank">
                  <p class="rank-item-header">
                    <n-gradient-text class="rank-item-header-number"> {{ item.rank }}.</n-gradient-text>
                    <n-avatar
                        :fallback-src="handleFallbackSrc(item)"
                        :size="24"
                        :src="item.avatar_url"
                        circle
                        style="margin-right: 10px"
                    />
                    <span class="rank-item-header-name">{{ item.user_name ? item.user_name : item.name }}</span>
                  </p>
                  <p class="rank-item-bq">
                    <span class="rank-item-bq-number">{{ item.influence }}</span>
                    <n-icon :size="16">
                      <radio/>
                    </n-icon>
                  </p>
                </div>
              </n-spin>
            </div>
            <div class="rank-pagination">
              <n-pagination
                  v-model:page="rankPage"
                  :page-count="rankPageCount"
                  :page-size="rankPageSize"
                  :simple="true"
                  size="small"
                  @update:page="handleRankPageChange"
              />
            </div>
            <div v-if="rankType === 'person'" class="self-rank rank-item">
              <p class="rank-item-header">
                <n-text class="rank-item-header-number"> {{ accountRank }}.</n-text>
                <n-avatar
                    :fallback-src="createAvatar(accountName.slice(0, 1))"
                    :size="24"
                    :src="avatarUrl"
                    circle
                    style="margin-right: 10px"
                />
                <span class="rank-item-header-name">{{ accountName }}</span>
              </p>
              <p class="rank-item-bq">
                <span class="rank-item-bq-number">{{ influenceScore }}</span>
                <n-icon :size="16">
                  <radio/>
                </n-icon>
              </p>
            </div>
          </n-card>
        </n-gi>
      </n-grid>
    </n-layout>
    <div class="page-footer">
      {{ `${config.name} ${config.version}·${config.license}` }}
    </div>
  </div>
  <n-modal
      v-model:show="showModal"
      preset="dialog"
      style="width: 75rem  /* 1200/16 */"
      title="选择您要进入的版本"
      transform-origin="center"
  >
    <n-data-table
        :columns="columns"
        :data="tableData"
        :loading="tableLoading"
        :pagination="productVersionPagination"
        :row-props="rowProps"
        remote
        @update:page="productVersionPageChange"
        @update:page-size="productVersionPageSizeChange"
    />
  </n-modal>
</template>
<script setup>
import {Check} from '@vicons/tabler';
import {Radio} from '@vicons/ionicons5';
import {storage} from '@/assets/utils/storageUtils';
import {createAvatar} from '@/assets/utils/createImg';
import {useRouter} from 'vue-router';
import {
  getAllOrg,
  getGroupAssetRank,
  getMsgGroup,
  getOrgStat,
  getUserAssetRank,
  getUserInfo
} from '@/api/get';
import titleImage from '@/assets/images/programming.png';
import AvatarGroup from '@/components/personalCenter/avatarGroup.vue';
import {Lock} from '@vicons/fa';
import config from '@/assets/config/settings';
import {ref} from 'vue';
import {useStore} from 'vuex';
import {
  columns,
  productVersionPageChange,
  productVersionPageSizeChange,
  getVersionTableData,
  getDefaultCheckNode,
  getRoundSelectList,
  getBranchSelectList,
  productVersionPagination,
  tableData,
  tableLoading,
  hasQualityboard,
  productId,
  detail,
  list
} from './modules/workspace';

const router = useRouter();
const orgAvatarSrc = ref(''); // 组织头像
const groupList = ref([]);
const userStat = ref();
const groupStat = ref();
const showModal = ref(false);
const totalGroupNum = ref(0);
const totalUserNum = ref(0);

const rowProps=(row)=>{
  return {
    style: 'cursor:pointer',
    onClick: () => {
      detail.value = row;
      // drawerShow.value = true;
      list.value = [];
      hasQualityboard.value = false;
      productId.value = row.id;
      getDefaultCheckNode(productId.value);
      getRoundSelectList(productId.value);
      getBranchSelectList(productId.value);
      router.push({name: 'dashboard', params: {workspace: 'release'}});
    }
  };
};
const getOrgStatistic = () => {
  getOrgStat(storage.getValue('loginOrgId')).then((res) => {
    totalGroupNum.value = res.data.total_groups;
    groupStat.value?.play();
    totalUserNum.value = res.data.total_users;
    userStat.value?.play();
  });
};

const clickDefaultWorkspace = () => {
  router.push({name: 'dashboard', params: {workspace: 'default'}});
};

const clickVersionWorkspace = () => {
  showModal.value = true;
};

const clickGroupWorkspace = (groupItem) => {
  if (groupItem.isAllowed) {
    router.push({name: 'automatic', params: {workspace: window.btoa(groupItem.id)}});
  }
};
// const onAfterLeave = () => {
//   // console.log(1);
//   router.push({name: 'dashboard', params: {workspace: 'release'}});
// };
const getOrgInfo = () => {
  getAllOrg({org_id: storage.getValue('loginOrgId')}).then((res) => {
    // orgAvatarSrc.value = res.data.avatar_url;
    res.data.forEach((item) => {
      if (item.org_id === storage.getValue('loginOrgId')) {
        orgAvatarSrc.value = item.org_avatar;
      }
    });
  });
};

const setAvatarList = (avatarList) => {
  return avatarList.map((item) => {
    return {
      name: item.user_name,
      src: item.avatar_url
    };
  });
};

const searchGroupValue = ref(null); // 团队查询条件
const groupPage = ref(1);
const groupPageSize = ref(12);
const groupTotal = ref(0);
const getGroupInfo = () => {
  getMsgGroup({page_num: groupPage.value, page_size: groupPageSize.value, name: searchGroupValue.value}).then(
      (res) => {
        groupList.value = [];
        res.data?.items.forEach((item) => {
          groupList.value.push({
            id: `group_${item.id}`,
            groupName: item.name,
            groupAvatarUrl: item.avatar_url,
            description: item.description,
            AvatarList: setAvatarList(item.admin_awatar),
            isAllowed: item.user_add_group_flag
          });
        });
        groupTotal.value = res.data.pages;
        groupPage.value = res.data.current_page;
      }
  );
};

const groupPageChange = (page) => {
  groupPage.value = page;
  getGroupInfo();
};

const groupPageSizeChange = (pageSize) => {
  groupPage.value = 1;
  groupPageSize.value = pageSize;
  getGroupInfo();
};

const searchValueChange = () => {
  groupPage.value = 1;
  getGroupInfo();
};

const loading = ref(false);
const rankType = ref('person');
const rankPage = ref(1);
const rankPageCount = ref(1);
const rankPageSize = ref(20);
const rankList = ref([]); // 影响力列表
const influenceScore = ref(0); // 影响力
const accountRank = ref(null); // 影响力等级
const accountName = ref(''); // 当前登录账号
const avatarUrl = ref(null); // 当前账号头像
const getRank = (asyncFunc) => {
  asyncFunc({page_num: rankPage.value, page_size: rankPageSize.value}).then((res) => {
    rankList.value = res.data.items;
    rankPage.value = res.data.current_page;
    rankPageCount.value = res.data.pages;
  });
};

const handleRankPageChange = () => {
  if (rankType.value === 'person') {
    getRank(getUserAssetRank);
  } else {
    getRank(getGroupAssetRank);
  }
};

// 头像加载失败显示的头像
function handleFallbackSrc(item) {
  if (item.user_name) {
    return createAvatar(item.user_name.slice(0, 1));
  }
  return null;
}

watch(rankType, () => {
  rankPage.value = 1;
  handleRankPageChange();
});

onMounted(() => {
  getOrgInfo();
  getGroupInfo();
  getOrgStatistic();
  getRank(getUserAssetRank);
  getUserInfo(storage.getValue('user_id')).then((res) => {
    accountName.value = res.data.user_name;
    accountRank.value = res.data.rank;
    avatarUrl.value = res.data.avatar_url;
    influenceScore.value = res.data.influence;
  });
  getVersionTableData({page_num: 1, page_size: 10});
});
//公告栏
const store = useStore();
const noticeList = store.state.notices.noticeList;
const docList = store.state.docs.docList;
</script>

<style lang="less" scoped>
.workspaces-container {
  height: 100%;
  width: 100%;
  .welcome-warp {
    padding: 20px;
    // background-image: linear-gradient(rgb(239, 240, 249) 0%, rgb(232, 233, 244) 99%);
    background-color: white;
    border-radius: 4px;
    position: relative;
    height: 250px;
    box-sizing: border-box;

    .detail-wrap {
      display: flex;
      align-items: center;
      height: 22px;

      .text {
        margin-left: 10px;
        line-height: 22px;
      }
    }

    .image-box {
      position: absolute;
      top: 0;
      right: 300px;
    }

    .stat-box {
      position: absolute;
      top: 50px;
      right: 50px;
    }
  }

  .workspaces-wrap {
    border-radius: 2px;
    padding: 10px;
    background-color: white;

    .workspaces-title {
      font-weight: 800;
      font-size: 16px;
      font-family: 'system-ui';
      color: rgba(0, 0, 0, 0.85);
    }

    .workspaces-content {
      margin-top: 20px;

      .publicworkspaces-wrap {
        display: flex;
        align-items: center;
        padding: 10px;
        height: 150px;
        cursor: pointer;
        background-color: rgb(255, 255, 255);
        box-shadow: rgb(0 0 0 / 15%) 0px 1px 5px 0px;
        border-radius: 4px;

        &:hover {
          box-shadow: rgb(0 0 0 / 20%) 0px 3px 20px 0px;
        }

        .detail-box {
          margin-left: 20px;
        }
      }

      .workspace-disabled {
        color: grey;
        cursor: not-allowed;
      }

      .group-workspaces-wrap {
        width: 100%;
        height: 100%;
        display: flex;
        flex-flow: row wrap;
        gap: 10px;
        margin-top: 10px;

        .group-workspace {
          width: calc((100% - 30px) / 4);

          .group-workspace-content {
            width: 100%;
            height: 110px;
            box-sizing: border-box;
            background-color: rgb(255, 255, 255);
            box-shadow: rgb(0 0 0 / 15%) 0px 1px 5px 0px;
            border-radius: 4px;
            padding-left: 12px;
            padding-right: 12px;
            padding-top: 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            cursor: pointer;
            position: relative;

            &:hover {
              box-shadow: rgb(0 0 0 / 20%) 0px 3px 20px 0px;
            }

            .detail {
              display: inline-flex;
              align-items: center;
              width: 100%;

              .image-wrap {
                width: 25%;
                display: flex;
                align-items: center;
                justify-content: center;
              }

              .name-user {
                margin-left: 15px;
                width: 75%;

                .name {
                  width: 100%;
                  font-weight: 500;
                  font-size: 16px;
                  color: rgba(0, 0, 0, 0.85);
                  overflow: hidden;
                  text-overflow: ellipsis;
                  white-space: nowrap;
                }

                .user-wrap {
                  display: inline-flex;
                  align-items: center;
                  width: 100%;
                }
              }
            }

            .description {
              width: 100%;
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
            }

            .lock-icon {
              position: absolute;
              top: 5px;
              right: 5px;
            }
          }
        }
      }

      .pagination-wrap {
        margin-top: 20px;
        display: flex;
        justify-content: flex-end;
      }
    }
  }

  .document-wrap {
    border-radius: 2px;
    padding: 10px;
    background-color: white;
    width: 100%;
    box-sizing: border-box;

    .document-title {
      display: flex;
      justify-content: space-between;

      .document-text {
        font-weight: 500;
        font-size: 16px;
        color: rgba(0, 0, 0, 0.85);
      }

      .view-all {
        font-weight: 400;
        color: rgba(0, 0, 0, 0.45);
        cursor: pointer;
      }
    }

    .document-content-wrap {
      margin-top: 10px;
      display: inline-flex;
      flex-direction: column;
      gap: 10px;
      width: 100%;

      .document-content {
        display: flex;
        cursor: pointer;
        gap: 8px;
        height: 20px;
        width: 100%;

        .content-type {
          padding: 0 7px;
          font-size: 12px;
          line-height: 20px;
          white-space: nowrap;
        }

        .content-text {
          width: 85%;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;

        }

        .document-first {
          color: white;
          background-color: #002fa7;
        }
      }
    }
  }

  .help-document {
    margin-top: 10px;
  }

  .page-footer {
    color: grey;
    background-image: linear-gradient(rgb(239, 240, 249) 0%, rgb(232, 233, 244) 99%);
    display: flex;
    align-items: center;
    justify-content: center;
    height: 80px;
  }
}

.hovered-card {
  border-radius: 2px;
}

.rank-wrap {
  margin-top: 20px;
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
  border-radius: 0 0 2px 2px;

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

a {
  text-decoration: none;
  color: #000;
}
</style>
