<template>
  <div class="workbench" ref="workbench">
    <div class="workbenchWrap">
      <n-alert title="系统公告" type="default" closable>
        <template #icon>
          <n-icon>
            <AnnouncementOutlined />
          </n-icon>
        </template>
        <div class="alert">暂无系统公告...</div>
      </n-alert>
      <grid-layout
        v-model:layout="layout"
        :col-num="12"
        :row-height="10"
        :is-draggable="true"
        :is-resizable="true"
        :is-mirrored="false"
        :vertical-compact="true"
        :margin="[10, 10]"
        :use-css-transforms="true"
      >
        <grid-item
          v-for="item in layout"
          :x="item.x"
          :y="item.y"
          :w="item.w"
          :h="item.h"
          :i="item.i"
          :minH="item.minH"
          :key="item.i"
          @resized="resizedEvent"
          dragIgnoreFrom=".ge-dashboard-module-body"
        >
          <div class="ge-dashboard-module" v-if="item.i === 'personal'">
            <div class="ge-dashboard-module-header">
              <div class="header-border" style="border-color: rgb(79, 211, 223)"></div>
              <div class="header-title d-flex flex-center flex-1 mr-2">
                <n-icon size="24">
                  <DragIndicatorFilled />
                </n-icon>
                <h2 class="header flex-1">个人数据概览</h2>
              </div>
              <div class="header-actions flex-shrink-0 d-flex flex-center ml-auto">
                <span class="action-item mr-2 refresh" title="刷新" ref="personalRefresh" @click="personalRefreshClick"
                  ><n-icon size="24"> <Refresh /> </n-icon
                ></span>
              </div>
            </div>
            <div class="ge-dashboard-module-body">
              <div class="ge-dashboard-module-statistics-view">
                <div class="ge-dashboard-module-statistics-view-content">
                  <div class="statistic">
                    <div class="label mb-2">今日任务</div>
                    <div class="value text-truncate">
                      {{ personalDataOverview.todayTasksCount }}
                    </div>
                  </div>
                  <div class="statistic">
                    <div class="label mb-2">本周任务</div>
                    <div class="value text-truncate">
                      {{ personalDataOverview.weekTasksCount }}
                    </div>
                  </div>
                  <div class="statistic">
                    <div class="label mb-2">本月任务</div>
                    <div class="value text-truncate">
                      {{ personalDataOverview.monthTasksCount }}
                    </div>
                  </div>
                  <div class="statistic">
                    <div class="label mb-2">今日贡献用例</div>
                    <div class="value text-truncate">
                      {{ personalDataOverview.todayCasesCount }}
                    </div>
                  </div>
                  <div class="statistic">
                    <div class="label mb-2">本周贡献用例</div>
                    <div class="value text-truncate">
                      {{ personalDataOverview.weekCasesCount }}
                    </div>
                  </div>
                  <div class="statistic">
                    <div class="label mb-2">本月贡献用例</div>
                    <div class="value text-truncate">
                      {{ personalDataOverview.monthCasesCount }}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="ge-dashboard-module" v-if="item.i === 'machine'">
            <div class="ge-dashboard-module-header">
              <div class="header-border" style="border-color: rgb(44, 126, 248)"></div>
              <div class="header-title d-flex flex-center flex-1 mr-2">
                <n-icon size="24">
                  <DragIndicatorFilled />
                </n-icon>
                <h2 class="header flex-1">我的机器</h2>
              </div>
              <div class="header-actions flex-shrink-0 d-flex flex-center ml-auto">
                <span class="action-item mr-2 refresh" title="刷新" ref="machineRefresh" @click="machineRefreshClick"
                  ><n-icon size="24"> <Refresh /> </n-icon
                ></span>
              </div>
            </div>
            <div class="ge-dashboard-module-body">
              <div class="ge-dashboard-module-collection-view">
                <div class="ge-dashboard-module-collection-view-header mb-3">
                  <div class="ge-tabs" @click="machineWorkbenchClick">
                    <a class="item" :class="{ active: machineActive === '0' }" data-index="0">虚拟机</a>
                    <a class="item" :class="{ active: machineActive === '1' }" data-index="1">物理机</a>
                  </div>
                  <div class="searchWrap ml-auto">
                    <n-icon size="22" class="search" @click="machineSearch">
                      <Search />
                    </n-icon>
                    <n-input type="text" placeholder="搜索..." class="input" v-model:value="machineSearchValue" />
                  </div>
                </div>
                <div class="ge-dashboard-module-collection-view-content">
                  <div class="ge-table-wrap" v-show="machineActive === '0'" @wheel.stop>
                    <n-data-table
                      :columns="myMachineColVirtual"
                      :data="myMachineData"
                      :bordered="false"
                      :single-column="true"
                      :bottom-bordered="false"
                    />
                  </div>
                  <div class="ge-table-wrap" v-show="machineActive === '1'" @wheel.stop>
                    <n-data-table
                      :columns="myMachineColPhysics"
                      :data="myMachineData"
                      :bordered="false"
                      :single-column="true"
                      :bottom-bordered="false"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="ge-dashboard-module" v-if="item.i === 'tasks'">
            <div class="ge-dashboard-module-header">
              <div class="header-border" style="border-color: rgb(95, 206, 96)"></div>
              <div class="header-title d-flex flex-center flex-1 mr-2">
                <n-icon size="24">
                  <DragIndicatorFilled />
                </n-icon>
                <h2 class="header flex-1">我的任务</h2>
              </div>
              <div class="header-actions flex-shrink-0 d-flex flex-center ml-auto">
                <span class="action-item mr-2 refresh" title="刷新" ref="taskRefresh" @click="taskRefreshClick"
                  ><n-icon size="24"> <Refresh /> </n-icon
                ></span>
              </div>
            </div>
            <div class="ge-dashboard-module-body">
              <div class="ge-dashboard-module-collection-view">
                <div class="ge-dashboard-module-collection-view-header mb-3">
                  <div class="ge-tabs" @click="taskWorkbenchClick">
                    <a class="item" :class="{ active: taskActive === '0' }" data-index="0">未完成</a>
                    <a class="item" :class="{ active: taskActive === '1' }" data-index="1">今日</a>
                    <a class="item" :class="{ active: taskActive === '2' }" data-index="2">本周</a>
                    <a class="item" :class="{ active: taskActive === '3' }" data-index="3">已逾期</a>
                    <a class="item" :class="{ active: taskActive === '4' }" data-index="4">所有</a>
                  </div>
                  <div class="searchWrap ml-auto">
                    <n-icon size="22" class="search" @click="taskSearch">
                      <Search />
                    </n-icon>
                    <n-input type="text" placeholder="搜索..." class="input" v-model:value="taskSearchValue" />
                  </div>
                </div>
                <div class="ge-dashboard-module-collection-view-content">
                  <div class="ge-table-wrap" @wheel.stop>
                    <n-data-table
                      :columns="myTasksCol"
                      :data="myTasksData"
                      :row-props="myTasksRowProps"
                      :bordered="false"
                      :single-column="true"
                      :bottom-bordered="false"
                      :pagination="tasksPagination"
                      remote
                      @update:page="handleTasksPageChange"
                      :loading="tasksloading"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="ge-dashboard-module" v-if="item.i === 'cases'">
            <div class="ge-dashboard-module-header">
              <div class="header-border" style="border-color: rgb(207, 39, 223)"></div>
              <div class="header-title d-flex flex-center flex-1 mr-2">
                <n-icon size="24">
                  <DragIndicatorFilled />
                </n-icon>
                <h2 class="header flex-1">我的用例状态</h2>
              </div>
              <div class="header-actions flex-shrink-0 d-flex flex-center ml-auto">
                <span class="action-item mr-2 refresh" title="刷新" ref="caseRefresh" @click="getMyCase"
                  ><n-icon size="24"> <Refresh /> </n-icon
                ></span>
              </div>
            </div>
            <div class="ge-dashboard-module-body">
              <div class="ge-dashboard-module-collection-view">
                <div class="ge-dashboard-module-collection-view-header mb-3">
                  <div class="ge-tabs" @click="caseWorkbenchClick">
                    <a class="item" :class="{ active: caseActive === '0' }" data-index="0">开启的</a>
                    <a class="item" :class="{ active: caseActive === '1' }" data-index="1">已合并</a>
                    <a class="item" :class="{ active: caseActive === '2' }" data-index="2">已关闭</a>
                    <a class="item" :class="{ active: caseActive === '3' }" data-index="3">全部</a>
                  </div>
                </div>
                <div class="ge-dashboard-module-collection-view-content">
                  <div class="ge-table-wrap" @wheel.stop>
                    <n-data-table
                      :columns="myCasesCol"
                      :data="myCasesData"
                      remote
                      :loading="caseLoading"
                      :pagination="myCasePagination"
                      :bordered="false"
                      @update:page="handleCasePageChange"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </grid-item>
      </grid-layout>
    </div>
  </div>
</template>

<script>
import { AnnouncementOutlined, DragIndicatorFilled } from '@vicons/material';
import { Refresh, Search } from '@vicons/tabler';
import modules from '@/views/dashboard/index';

export default defineComponent({
  components: {
    AnnouncementOutlined,
    DragIndicatorFilled,
    Refresh,
    Search
  },
  methods: {},
  setup() {
    modules.initData();
    return {
      ...modules
    };
  }
});
</script>

<style scoped lang="less">
.mode-fade-enter-active,
.mode-fade-leave-active {
  transition: opacity 0.5s ease;
}

.mode-fade-enter-from,
.mode-fade-leave-to {
  opacity: 0;
}

.workbench {
  padding: 24px 36px;
  box-sizing: border-box;
  background-color: #fcfcfc;

  .alert {
    height: 100px;
  }
}

.mr-1 {
  margin-right: 4px !important;
}
.mr-2 {
  margin-right: 8px !important;
}
.mb-2 {
  margin-bottom: 8px !important;
}
.mb-3 {
  margin-bottom: 12px !important;
}
.ml-auto {
  margin-left: auto !important;
}
:deep(.d-flex) {
  display: flex !important;
}
:deep(.flex-center) {
  align-items: center;
}
.flex-1 {
  flex: 1;
}
.flex-shrink-0 {
  flex-shrink: 0 !important;
}
.text-truncate {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.ge-dashboard-module {
  flex: auto;
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-shadow: inset 0 0 0 1px #ecedf0;
  background-color: #fff;
  border-radius: 6px;
  overflow: hidden;

  .ge-dashboard-module-header {
    flex: none;
    display: flex;
    align-items: center;
    box-sizing: border-box;
    width: 100%;
    height: 72px;
    padding: 0 24px;

    .header-border {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      display: block;
      border-top: 5px solid transparent;
      border-top-left-radius: 6px;
      border-top-right-radius: 6px;
      pointer-events: none;
    }

    .header-title {
      min-width: 0;
      height: 100%;
      cursor: -webkit-grab;
      cursor: grab;

      .header {
        min-width: 0;
        margin: 0;
        font-size: 16px;
        line-height: 24px;
        font-weight: 600;
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
        color: var(--text-color);
        border: none;
        padding: 0;
        text-transform: none;
      }
    }

    .header-actions {
      .action-item {
        // display: flex;
        display: inline-block;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border-radius: 4px;
        cursor: pointer;
        color: #909aaa;
        color: var(--text-muted-color);
        font-size: 20px;
        line-height: 24px;
        text-align: center;
      }

      .refresh {
        transition: 2s;
        transform: rotate(0);
      }
    }
  }

  .ge-dashboard-module-body {
    flex: 1;
    min-height: 0;
    position: relative;
    width: 100%;
    height: 100%;
    padding: 0 24px 24px;
    box-sizing: border-box;

    .ge-dashboard-module-statistics-view {
      display: flex;
      flex-direction: column;
      height: 100%;

      .ge-dashboard-module-statistics-view-content {
        flex: 1;
        min-height: 0;
        overflow-y: auto;
        display: flex;
        flex-wrap: wrap;

        .statistic {
          flex: 1 1 0;
          min-width: 80px;
          border-radius: 4px;
          padding: 12px 0;
          margin: 4px 0 !important;
          display: flex;
          flex-direction: column;
          justify-content: center;
          text-decoration: none;

          .label {
            margin-top: 0;
            font-size: 13px;
            font-weight: 400;
            line-height: 18px;
            color: var(--text-color);
            text-transform: uppercase;
            text-align: center;
          }

          .value {
            font-size: 24px !important;
            font-weight: 300;
            line-height: 28px;
            margin-top: 0;
            color: var(--text-color);
            text-transform: uppercase;
            text-align: center;
          }
        }
      }
    }

    .ge-dashboard-module-collection-view {
      display: flex;
      flex-direction: column;
      height: 100%;

      .ge-dashboard-module-collection-view-header {
        flex-shrink: 0;
        display: flex;
        flex-direction: row;
        justify-content: space-between;
        align-items: center;

        .ge-tabs {
          margin: 0;
          min-height: 0;
          border-bottom: 0;
          white-space: nowrap;
          border-color: var(--divider-color);
          background: none;
          border-radius: 0;
          border: none;
          box-shadow: none;
          font-size: 1rem;
          display: flex;
          font-weight: 400;

          .item {
            margin-bottom: 0;
            cursor: pointer;
            opacity: 0.8;
            display: inline-block;
            font-size: 1rem;
            line-height: 20px;
            padding: 2px 16px 4px;
            color: var(--text-muted-color);
            border-radius: 0;
            align-self: flex-end;
            margin: 0 0 -2px;
            border-bottom: 2px solid transparent;
            transition: color 0.1s ease;
            box-shadow: none;
            background: none;
            align-items: center;
            position: relative;
            vertical-align: middle;
            text-decoration: none;
            -webkit-tap-highlight-color: transparent;
            flex: 0 0 auto;
            user-select: none;
            text-transform: none;
            font-weight: 400;
          }

          .active {
            border-color: #2c7ef8 !important;
            color: #2c7ef8 !important;
            background-color: transparent;
            box-shadow: none;
          }
        }

        .searchWrap {
          margin: 1px 0;
          font-size: 0.92857143em;
          position: relative;
          font-weight: 400;
          font-style: normal;
          display: inline-flex;
          color: #2e405e;
          width: 50%;

          .search {
            position: absolute;
            top: 5px;
            right: 5px;
            z-index: 999;
          }

          .input {
            padding-right: 18px;
          }
        }
      }

      .ge-dashboard-module-collection-view-content {
        flex: 1;
        min-height: 0;
        overflow-y: auto;

        .ge-table-wrap {
          overflow: visible;

          // :deep(.n-data-table-thead) {
          //   display: none !important;
          // }

          :deep(i) {
            vertical-align: middle;
          }
        }
      }
    }
  }

  .ge-dashboard-module-footer {
    flex-shrink: 0;
    min-height: 24px;
    padding: 0 24px 24px;
  }
}
</style>
