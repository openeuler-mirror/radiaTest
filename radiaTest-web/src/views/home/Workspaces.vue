<template>
  <div class="workspaces-container">
    <n-layout
      embedded
      :content-style="{
        padding: '24px',
        backgroundColor: '#f5f5f5'
      }"
      :style="{
        height: '100%'
      }"
    >
      <div class="welcome-warp">
        <H2>Hi，欢迎使用开源测试管理平台radiaTest！</H2>
        <p>radiaTest提供一站式自动化测试集成、管理、执行、分析、以及跨团队、跨企业质量写作能力。</p>
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
          <div class="text">多元化测试引擎，满足社区差异化测试能力需求，灵活选用</div>
        </div>
        <div class="detail-wrap">
          <n-icon color="#429cee">
            <Check></Check>
          </n-icon>
          <div class="text">任务管理管理能力，实现测试活动全流程承载</div>
        </div>
        <div class="image-box">
          <n-image height="250" width="500" :src="titleImage" preview-disabled />
        </div>
      </div>
      <n-grid :cols="12" x-gap="24" style="margin-top: 20px">
        <n-gi :span="10">
          <div class="workspaces-wrap">
            <div class="workspaces-title">Workspace</div>
            <n-collapse :default-expanded-names="['publicWorkspaces', 'groupWorkspaces']" class="workspaces-content">
              <n-collapse-item title="公共workspaces" name="publicWorkspaces">
                <n-grid :cols="2" x-gap="24">
                  <n-gi :span="1">
                    <div class="publicworkspaces-wrap" @click="clickDefaultWorkspace">
                      <div>
                        <n-avatar :size="100" :src="orgAvatarSrc"> </n-avatar>
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
                    <div class="publicworkspaces-wrap" @click="clickVersionWorkspace" style="color: grey">
                      <div>
                        <n-avatar :size="100" :src="orgAvatarSrc"> </n-avatar>
                      </div>
                      <div class="detail-box">
                        <h3>版本级workspace</h3>
                        <p>
                          当前组织下的版本级视图，主要围绕当前待发布版本的测试活动展开，全局展示当前版本迭代阶段与质量状况
                        </p>
                      </div>
                    </div>
                  </n-gi>
                </n-grid>
              </n-collapse-item>
              <n-collapse-item title="团队workspaces" name="groupWorkspaces">
                <n-tabs type="line">
                  <n-tab name="all"> 全部 </n-tab>
                  <n-tab name="myJoin"> 我加入的 </n-tab>
                  <n-tab name="myCreate"> 我创建的 </n-tab>
                </n-tabs>
                <template #header-extra>
                  <n-input
                    v-model:value="searchGroupValue"
                    clearable
                    placeholder="请输入团队名称"
                    @click.stop.prevent
                    @change="searchValueChange"
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
                            width="50"
                            :src="groupItem.groupAvatarUrl"
                            :fallback-src="createAvatar(groupItem.groupName.slice(0, 1))"
                          />
                        </div>
                        <div class="name-user">
                          <div class="name">{{ groupItem.groupName }}</div>
                          <div class="user-wrap">
                            <AvatarGroup :options="groupItem.AvatarList" :size="30" :max="3" />
                          </div>
                        </div>
                      </div>
                      <span class="description">{{ groupItem.description }}</span>
                    </div>
                  </div>
                </div>
                <n-pagination
                  class="pagination-wrap"
                  v-model:page="groupPage"
                  v-model:page-size="groupPageSize"
                  :page-count="groupTotal"
                  show-size-picker
                  :page-sizes="[12, 24, 48, 100]"
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
            <div class="document-content-wrap">
              <div class="document-content">
                <div class="content-type document-first">升级</div>
                <div class="content-text">发布记录-V1.2.1(2023.03.02)</div>
              </div>
              <div class="document-content">
                <div class="content-type">升级</div>
                <div class="content-text">发布记录-V1.2.0(2023.02.15)</div>
              </div>
            </div>
          </div>
          <div class="document-wrap help-document">
            <div class="document-title">
              <div class="document-text">帮助文档</div>
              <div class="view-all">查看全部</div>
            </div>
            <div class="document-content-wrap">
              <div class="document-content">
                <div class="content-type document-first">文档</div>
                <div class="content-text">架构简介</div>
              </div>
              <div class="document-content">
                <div class="content-type">文档</div>
                <div class="content-text">安装教程</div>
              </div>
              <div class="document-content">
                <div class="content-type">文档</div>
                <div class="content-text">基于裸金属/虚拟机节点容器化部署的运维说明</div>
              </div>
              <div class="document-content">
                <div class="content-type">文档</div>
                <div class="content-text">参与贡献</div>
              </div>
              <div class="document-content">
                <div class="content-type">文档</div>
                <div class="content-text">Commit规范 & 质量要求</div>
              </div>
              <div class="document-content">
                <div class="content-type">文档</div>
                <div class="content-text">联系方式</div>
              </div>
              <div class="document-content">
                <div class="content-type">文档</div>
                <div class="content-text">特技</div>
              </div>
            </div>
          </div>
          <n-card
            class="hovered-card rank-wrap"
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
                >个人积分</n-tab
              >
              <n-tab
                name="group"
                @click="
                  () => {
                    rankType = 'group';
                  }
                "
                >团队积分</n-tab
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
        </n-gi>
      </n-grid>
    </n-layout>
  </div>
</template>
<script setup>
import { Check } from '@vicons/tabler';
import { Radio } from '@vicons/ionicons5';
import { storage } from '@/assets/utils/storageUtils';
import { createAvatar } from '@/assets/utils/createImg';
import { useRouter } from 'vue-router';
import { getUserAssetRank, getGroupAssetRank, getUserInfo, getAllOrg, getMsgGroup } from '@/api/get';
import titleImage from '@/assets/images/programming.png';
import AvatarGroup from '@/components/personalCenter/avatarGroup.vue';

const router = useRouter();

const orgAvatarSrc = ref(''); // 组织头像
const groupList = ref([]);

const clickDefaultWorkspace = () => {
  router.push({ name: 'dashboard', params: { workspace: 'default' } });
};

const clickVersionWorkspace = () => {
  // router.push({ name: 'dashboard', params: { workspace: 'release' } });
};

const clickGroupWorkspace = (groupItem) => {
  router.push({ name: 'automatic', params: { workspace: window.btoa(groupItem.id) } });
};

const getOrgInfo = () => {
  getAllOrg({ org_id: storage.getValue('orgId') }).then((res) => {
    // orgAvatarSrc.value = res.data.avatar_url;
    res.data.forEach((item) => {
      if (item.org_id === storage.getValue('orgId')) {
        orgAvatarSrc.value = item.org_avatar;
      }
    });
  });
};

const setAvatarList = (list) => {
  return list.map((item) => {
    return {
      name: item.gitee_name,
      src: item.avatar_url
    };
  });
};

const searchGroupValue = ref(null); // 团队查询条件
const groupPage = ref(1);
const groupPageSize = ref(12);
const groupTotal = ref(0);

const getGroupInfo = () => {
  getMsgGroup({ page_num: groupPage.value, page_size: groupPageSize.value, name: searchGroupValue.value }).then(
    (res) => {
      groupList.value = [];
      res.data?.items.forEach((item) => {
        groupList.value.push({
          id: `group_${item.id}`,
          groupName: item.name,
          groupAvatarUrl: item.avatar_url,
          description: item.description,
          AvatarList: setAvatarList(item.admin_awatar)
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
  asyncFunc({ page_num: rankPage.value, page_size: rankPageSize.value }).then((res) => {
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
  if (item.gitee_name) {
    return createAvatar(item.gitee_name.slice(0, 1));
  }
  return null;
}

watch(rankType, () => {
  handleRankPageChange();
});

onMounted(() => {
  getOrgInfo();
  getGroupInfo();
  getRank(getUserAssetRank);
  getUserInfo(storage.getValue('gitee_id')).then((res) => {
    accountName.value = res.data.gitee_name;
    accountRank.value = res.data.rank;
    avatarUrl.value = res.data.avatar_url;
    influenceScore.value = res.data.influence;
  });
});
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
      right: 200px;
    }
  }

  .workspaces-wrap {
    border-radius: 2px;
    padding: 10px;
    background-color: white;

    .workspaces-title {
      font-weight: 500;
      font-size: 16px;
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

        .detail-box {
          margin-left: 20px;
        }
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
          }
        }
      }

      .pagination-wrap {
        margin-top: 20px;
        display: flex;
        justify-content: end;
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
</style>
