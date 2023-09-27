<template>
  <div ref="workbench" class="workbench">
    <div class="workbenchWrap" v-if="$route.params.workspace==='default'">
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
                  ><n-icon size="24"> <Refresh /> </n-icon></span>
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
    <div v-if="$route.params.workspace==='release'">
      <n-modal v-model:show="showChecklistBoard">
        <n-card
            :bordered="false"
            aria-modal="true"
            role="dialog"
            size="huge"
            style="width: 1000px"
            title="检查项比对结果"
        >
          <n-data-table
              :columns="checklistBoardTableColumns"
              :data="checklistBoardTableData"
              :loading="checklistBoardTableLoading"
              :pagination="checklistBoardTablePagination"
              @update:page="checklistBoardTablePageChange"
              @update:page-size="checklistBoardTablePageSizeChange"
          />
        </n-card>
      </n-modal>
      <n-modal v-model:show="showRoundMilestoneBoard" @update:show="updateRoundMilestoneBoard">
        <RoundRelateMilestones :ProductId="productId" :currentRound="currentRound"></RoundRelateMilestones>
      </n-modal>
      <div id="drawer-target">
        <div style="display: flex; align-items: center">
          <n-h3 style="margin: 0; padding: 0">
            {{ `${detail.name}-${detail.version}` }}
          </n-h3>
        </div>
      </div>
      <div class="drawer-content">
        <n-grid x-gap="12" :cols="3">
          <n-gi :span="3" style="margin-top: 40px; margin-bottom: 20px">
            <autoSteps
                @stepClick="handleClick"
                @rollback="handleRollback"
                @haveDone="haveDone"
                @haveRecovery="haveRecovery"
                @add="stepAdd"
                @handleChecklistBoard="handleChecklistBoard"
                @handleMilestone="handleMilestone"
                :done="done"
                :list="list"
                :currentId="currentId"
                :hasQualityboard="hasQualityboard"
            />
          </n-gi>
        </n-grid>
        <n-grid v-if="list.length" :cols="3" x-gap="16">
          <!-- 问题解决统计 -->
          <n-gi v-if="!showPackage && !showList" :span="1">
            <div
                :style="{
                  backgroundColor:
                    issuesResolvedPassed !== null ? (issuesResolvedPassed ? '#D5E8D4' : 'white') : 'white',
                  border:
                    issuesResolvedPassed !== null
                      ? issuesResolvedPassed
                        ? '1px solid #A2C790'
                        : '1px solid #B95854'
                      : '1px solid #ddddd'
                }"
                class="card inout-animated"
                @click="cardClick"
            >
              <div class="topselect">
                <n-popselect
                    v-model:value="resolvedMilestone"
                    :options="resolvedMilestoneOptions"
                    trigger="click"
                    @update:value="selectResolvedMilestone"
                >
                  <n-button text @click.stop>{{ resolvedMilestone.name || '当前迭代' }}</n-button>
                </n-popselect>
              </div>
              <n-progress
                  :percentage="currentResolvedRate"
                  :status="
                    currentResolvedPassed !== true ? (currentResolvedPassed === false ? 'error' : 'default') : 'success'
                  "
                  :stroke-width="9"
                  class="topProgress"
                  type="circle"
              >
                  <span style="text-align: center; font-size: 33px">
                    {{ currentResolvedRate ? `${currentResolvedRate}%` : '0%' }}
                  </span>
              </n-progress>
              <div style="display: flex; position: absolute; top: 4%; left: 73%">
                <n-icon size="20" style="margin-right: 5px">
                  <CheckCircleFilled v-if="issuesResolvedPassed" color="#18A058"/>
                  <QuestionCircle16Filled v-else-if="issuesResolvedPassed === null"/>
                  <CancelRound v-else color="#D03050"/>
                </n-icon>
                <span>
                    {{ issuesResolvedPassed !== null ? (issuesResolvedPassed ? '已达标' : '未达标') : 'unknown' }}
                  </span>
              </div>
              <div style="position: absolute; left: 61%; top: 16%; text-align: center">
                <span style="font-size: 20px"> 问题解决统计 </span><br/>
                <span style="font-size: 20px; color: #929292"> 当前迭代 </span>
                <p style="font-size: 30px; margin-top: 3px; margin-bottom: 3px">
                  {{ currentAllCnt && currentResolvedRate ? `${currentResolvedCnt}/${currentAllCnt}` : '0/0' }}
                </p>
                <div style="display: flex; align-items: center; justify-content: space-around">
                  <div style="display: flex; flex-direction: column">
                    <p style="font-size: 14px; margin: 0">遗留问题数</p>
                  </div>
                  <p :style="{ fontSize: '30px' }">
                    {{ leftIssuesCnt ? leftIssuesCnt : '0' }}
                  </p>
                </div>
              </div>
              <div
                  class="description"
                  style="font-size: 19px; position: absolute; top: 69%; display: flex; justify-content: space-around"
              >
                <span> 严重/主要问题解决率 </span>
                <span>
                    {{
                    seriousMainResolvedCnt && seriousMainAllCnt
                        ? `${seriousMainResolvedCnt}/${seriousMainAllCnt}`
                        : '0/0'
                  }}
                  </span>
              </div>
              <n-progress
                  :border-radius="4"
                  :fill-border-radius="0"
                  :height="20"
                  :indicator-placement="'inside'"
                  :percentage="seriousMainResolvedRate"
                  :status="
                    seriousMainResolvedPassed !== true
                      ? seriousMainResolvedPassed === false
                        ? 'error'
                        : 'default'
                      : 'success'
                  "
                  processing
                  style="position: absolute; width: 78%; top: 80%; left: 11%"
                  type="line"
              />
              <n-tooltip>
                <template #trigger>
                  <n-progress
                      :percentage="seriousResolvedRate"
                      :status="
                        seriousResolvedPassed !== true
                          ? seriousResolvedPassed === false
                            ? 'error'
                            : 'default'
                          : 'success'
                      "
                      style="position: absolute; width: 78%; top: 86%; left: 11%"
                      type="line"
                  />
                </template>
                严重问题解决率{{ seriousResolvedRate }}%
              </n-tooltip>
              <n-tooltip>
                <template #trigger>
                  <n-progress
                      :percentage="mainResolvedRate"
                      :status="
                        mainResolvedPassed !== true ? (mainResolvedPassed === false ? 'error' : 'default') : 'success'
                      "
                      style="position: absolute; width: 78%; top: 91%; left: 11%"
                      type="line"
                  />
                </template>
                主要问题解决率{{ mainResolvedRate }}%
              </n-tooltip>
            </div>
          </n-gi>
          <n-gi ref="requestCard" :span="showList || showPackage ? 3 : 2">
            <!-- 特性 -->
            <div
                v-if="!showPackage"
                :style="{
                  width: showList === false ? '100%' : boxWidth + 'px'
                }"
                class="transitionBox"
            >
              <div
                  v-if="!showList"
                  class="card"
                  style="display: flex; justify-content: space-evenly; height: 100%; background: white"
                  @click="handleListClick"
              >
                <div class="featureProgress">
                  <echart :option="additionFeatureOption" chartId="additionFeaturePieChart"/>
                </div>
                <div class="featureProgress">
                  <echart :option="inheritFeatureOption" chartId="inheritFeaturePieChart"/>
                </div>
              </div>
              <div v-if="showList">
                <n-card style="height: auto; box-shadow: 0 2px 8px 0 rgb(2 24 42 / 10%)">
                  <template #header>
                    <span>新增/继承特性测试任务跟踪</span>
                  </template>
                  <template #header-extra>
                    <n-icon style="cursor: pointer" @click="showList = false">
                      <MdClose/>
                    </n-icon>
                  </template>
                  <n-tabs animated type="line">
                    <n-tab-pane name="addition" tab="新增测试需求">
                      <feature-table :qualityboard-id="dashboardId" type="addition"/>
                    </n-tab-pane>
                    <n-tab-pane name="inherit" tab="继承测试需求">
                      <feature-table :qualityboard-id="dashboardId" type="inherit"/>
                    </n-tab-pane>
                  </n-tabs>
                </n-card>
              </div>
            </div>
            <!-- 软件包 -->
            <n-card
                v-if="!showList"
                :bordered="false"
                :style="{
                  height: showPackage ? 'auto' : ''
                }"
                class="cardbox inout-animated"
                title="软件包变更"
            >
              <template v-if="showPackage" #header-extra>
                <n-icon style="cursor: pointer" @click="showPackage = false">
                  <MdClose/>
                </n-icon>
              </template>
              <template v-else #header-extra>
                <n-popover>
                  <template #trigger>
                    <n-button circle quaternary @click="showDailyBuildModal">
                      <template #icon>
                        <n-icon :size="18">
                          <BuildCircleOutlined/>
                        </n-icon>
                      </template>
                    </n-button>
                  </template>
                  获取每日构建软件范围
                </n-popover>
                <refresh-button
                    :size="18"
                    @refresh="
                      getPackageListComparationSummary(dashboardId, {
                        refresh: true,
                        repoPath: 'everything',
                        arch: 'all'
                      })
                    "
                >
                  获取最新软件包变更数据
                </refresh-button>
              </template>
              <div class="transitionBox">
                <div
                    v-if="!showPackage"
                    style="display: flex; justify-content: space-around; height: 100%"
                    @click="handlePackageCardClick"
                >
                  <div class="packageCard transitionBox">
                    <div class="package-left">
                      <n-h3 style="font-size: 33px">
                        {{ oldPackage.size }}
                      </n-h3>
                      <p>{{ oldPackage.name }}</p>
                    </div>
                    <div class="package-middle">
                      <p style="font-size: 15px; margin-top: 0px">
                        <span>+{{ packageChangeSummary.addPackagesNum }}</span>
                      </p>
                      <p style="font-size: 15px; margin-top: 0px">
                        <span>-{{ packageChangeSummary.delPackagesNum }}</span>
                      </p>
                      <n-icon color="green" size="20">
                        <DoubleArrowFilled/>
                      </n-icon>
                    </div>
                    <div class="package-right">
                      <n-h3 style="font-size: 33px">
                        {{ newPackage.size }}
                      </n-h3>
                      <p>{{ newPackage.name }}</p>
                    </div>
                  </div>
                </div>
                <!-- 软件包变更详情卡片 -->
                <div v-if="showPackage">
                  <n-tabs
                      v-model:value="currentPanel"
                      :closable="packageCompareClosable"
                      addable
                      animated
                      type="card"
                      @add="handlePackageCompareAdd"
                      @close="handlePackageCompareClose"
                  >
                    <n-tab-pane
                        v-for="packageComparePanel in packageComparePanels"
                        :key="packageComparePanel"
                        :name="packageComparePanel.id"
                        :tab="`对比${packageComparePanel.name}`"
                    >
                      <n-tabs
                          v-model:value="packageTabValueFirst"
                          animated
                          type="line"
                          @update:value="changePackageTabFirst"
                      >
                        <n-tab name="softwarescope"> 软件范围</n-tab>
                        <n-tab v-if="currentPanel === 'fixed'" name="homonymousIsomerism"> 同名异构</n-tab>
                      </n-tabs>
                      <n-tabs
                          v-model:value="packageTabValueSecond"
                          animated
                          type="line"
                          @update:value="changePackageTabSecond"
                      >
                        <n-tab name="everything"> everything</n-tab>
                        <n-tab name="EPOL"> EPOL</n-tab>
                        <n-tab v-if="packageTabValueFirst!=='homonymousIsomerism'" name="source"> source</n-tab>
                        <n-tab
                            v-if="currentPanelDetail.type === 'release' && currentRound.type === 'release'"
                            name="update"
                        >
                          update
                        </n-tab>
                      </n-tabs>
                      <div v-show="packageTabValueFirst !== 'homonymousIsomerism'" class="packageCard">
                        <div class="package-left">
                          <n-h3>
                            {{ oldPackage.size }}
                          </n-h3>
                          <p>{{ oldPackage.name }}</p>
                        </div>
                        <div class="package-middle">
                          <p style="font-size: 15px; margin-top: 0px">
                            <span>+{{ packageChangeSummary.addPackagesNum }}</span>
                          </p>
                          <p style="font-size: 15px; margin-top: 0px">
                            <span>-{{ packageChangeSummary.delPackagesNum }}</span>
                          </p>
                          <n-icon color="green">
                            <DoubleArrowFilled/>
                          </n-icon>
                        </div>
                        <div class="package-right">
                          <n-h3>
                            {{ newPackage.size }}
                          </n-h3>
                          <p>{{ newPackage.name }}</p>
                        </div>
                      </div>
                      <package-table
                          :hasMultiVersionPackage="hasMultiVersionPackage"
                          :packageTabValueFirst="packageTabValueFirst"
                          :packageTabValueSecond="packageTabValueSecond"
                          :qualityboard-id="dashboardId"
                          :round-cur-id="currentId"
                          :roundCompareeId="roundCompareeId"
                      />
                    </n-tab-pane>
                  </n-tabs>
                  <n-modal v-model:show="showAddNewCompare" preset="dialog" title="Dialog">
                    <template #header>
                      <div>新增比对</div>
                    </template>
                    <div>
                      <n-form :model="newCompareForm">
                        <n-form-item label="版本" path="product">
                          <n-select
                              v-model:value="newCompareForm.product"
                              :loading="productLoading"
                              :options="productOptions"
                              filterable
                              placeholder="请选择比对的基线版本"
                          />
                        </n-form-item>
                        <n-radio-group v-model:value="newCompareForm.type">
                          <n-space>
                            <n-radio value="release"> 发布版本</n-radio>
                            <n-radio value="round"> 迭代轮次</n-radio>
                          </n-space>
                        </n-radio-group>
                        <n-form-item path="round">
                          <n-select
                              v-model:value="newCompareForm.round"
                              :loading="roundLoading"
                              :options="roundOptions"
                              filterable
                          />
                        </n-form-item>
                      </n-form>
                    </div>
                    <template #action>
                      <n-button type="primary" @click="handleNewCompareCreate"> 提交</n-button>
                    </template>
                  </n-modal>
                </div>
              </div>
            </n-card>
          </n-gi>
          <n-gi :span="2" style="margin-top: 10px">
            <div class="middledowload">
              <n-popselect
                  v-model:value="roundId"
                  :options="roundIdOptions"
                  @update:value="selectRound"
              >
                <n-button class="selectbutton " @click.stop>{{ roundId.name || '选择round' }}</n-button>
              </n-popselect>

              <n-popselect
                  v-model:value="branch"
                  :options="branchOptions"
              >
                <n-button class="selectbutton marginbutton" @click.stop>{{ branch.name || '选择分支' }}</n-button>
              </n-popselect>

              <n-button :loading="loadingRef" ghost type="primary" @click.stop="exportQualityHistoryFn">
                <template #icon>
                  <n-icon>
                    <FileExport/>
                  </n-icon>
                </template>
                质量报告导出
              </n-button>
            </div>
          </n-gi>
          <n-gi :span="2" style="margin-top: 5px">
            <n-tabs v-model:value="activeTab" animated type="line">
              <n-tab-pane name="testProgress" tab="测试进展"></n-tab-pane>
              <n-tab-pane name="qualityProtect" tab="质量防护网"></n-tab-pane>
              <n-tab-pane :disabled="true" name="performance" tab="性能看板"></n-tab-pane>
              <n-tab-pane :disabled="true" name="compatibility" tab="兼容性看板"></n-tab-pane>
            </n-tabs>
            <div>
              <keep-alive>
                <test-progress v-if="activeTab === 'testProgress'" :defaultMilestoneId="defaultMilestoneId"/>
                <quality-protect v-else-if="activeTab === 'qualityProtect'" :quality-board-id="dashboardId"/>
              </keep-alive>
            </div>
          </n-gi>
        </n-grid>
        <n-empty
            v-else
            description="未通过质量checklist，无法开启第一轮迭代测试"
            size="huge"
            style="justify-content: center; height: 100%"
        />
        <!-- issue 弹窗 -->
        <n-drawer
            v-model:show="active"
            :mask-closable="false"
            :trap-focus="false"
            height="100%"
            placement="right"
            width="95%"
        >
          <n-drawer-content closable>
            <MilestoneIssuesCard :cardType="MilestoneIssuesCardType" :milestone-id="resolvedMilestone.id"/>
          </n-drawer-content>
        </n-drawer>
      </div>
      <!--      TODO:页面样式的重整-->
    </div>
  </div>
</template>

<script>
import {BuildCircleOutlined, CancelRound, CheckCircleFilled, DoubleArrowFilled,} from '@vicons/material';
import {FileExport} from '@vicons/tabler';
import modules from '@/views/dashboard/index';
import {useRoute} from 'vue-router';
import {
  active,
  activeTab,
  additionFeatureSummary,
  branch,
  branchOptions,
  checklistBoardTableColumns,
  checklistBoardTableData,
  checklistBoardTableLoading,
  checklistBoardTablePagination,
  currentAllCnt,
  currentId,
  currentPanel,
  currentPanelDetail,
  currentProduct,
  currentResolvedCnt,
  currentResolvedPassed,
  currentResolvedRate,
  currentRound,
  dashboardId,
  detail,
  done,
  hasMultiVersionPackage,
  hasQualityboard,
  inheritFeatureSummary,
  issuesResolvedPassed,
  leftIssuesCnt,
  leftIssuesPassed,
  list,
  loadingRef,
  mainResolvedPassed,
  mainResolvedRate,
  newCompareForm,
  newPackage,
  oldPackage,
  packageChangeSummary,
  packageCompareClosable,
  packageComparePanels,
  packageTabValueFirst,
  packageTabValueSecond,
  productId,
  productList,
  productLoading,
  productOptions,
  productVersionPagination,
  resolvedMilestone,
  resolvedMilestoneOptions,
  roundCompareeId,
  roundId,
  roundIdOptions,
  roundLoading,
  roundOptions,
  seriousMainAllCnt,
  seriousMainResolvedCnt,
  seriousMainResolvedPassed,
  seriousMainResolvedRate,
  seriousResolvedPassed,
  seriousResolvedRate,
  showAddNewCompare,
  showChecklistBoard,
  showList,
  showPackage,
  showRoundMilestoneBoard,
    boxWidth,
    MilestoneIssuesCardType,
    defaultMilestoneId,
    requestCard,
  changePackageTabFirst,
  changePackageTabSecond,
  checklistBoardTablePageChange,
  checklistBoardTablePageSizeChange,
  selectResolvedMilestone,
  selectRound,
  showDailyBuildModal,
  stepAdd,
  updateRoundMilestoneBoard,
  exportQualityHistoryFn,
  getBranchSelectList,
  getPackageChangeSummary,
  getPackageListComparationSummary,
  getVersionTableData,
  handleChecklistBoard,
  handleClick,
  handleListClick,
  handleMilestone,
  handleNewCompareCreate,
  handlePackageCardClick,
  handlePackageCompareAdd,
  handlePackageCompareClose,
  handleRollback,
  haveDone,
  haveRecovery,
  cleanPackageListData
} from '@/views/home/modules/workspace';
import {MdClose} from '@vicons/ionicons4';
import {QuestionCircle16Filled} from '@vicons/fluent';
import {featureOption, setFeatureOption} from '@/views/versionManagement/product/modules/featureProgress';
import {getProductVersionOpts} from '@/assets/utils/getOpts';
import {onMounted, onUnmounted, reactive, watch} from 'vue';

export default defineComponent({
  components: {
    QuestionCircle16Filled,
    FileExport,
    BuildCircleOutlined,
    DoubleArrowFilled,
    CheckCircleFilled,
    MdClose,
    CancelRound,
  },
  methods: {},
  setup() {
    const additionFeatureOption = reactive(JSON.parse(JSON.stringify(featureOption)));
    const inheritFeatureOption = reactive(JSON.parse(JSON.stringify(featureOption)));
    const route = useRoute();
    if (route.params.workspace === 'default') {
      modules.initData();
    }
    const refreshTableData = () => {
      getVersionTableData({
        page_num: 1,
        page_size: productVersionPagination.value.pageSize
      });
    };
    onMounted(() => {
      if(route.params.workspace==='release'){
        getVersionTableData({
          page_num: productVersionPagination.value.page,
          page_size: productVersionPagination.value.pageSize
        });
        getProductVersionOpts(productList);
        setFeatureOption(additionFeatureOption, '新增特性', additionFeatureSummary.value);
        setFeatureOption(inheritFeatureOption, '继承特性', inheritFeatureSummary.value);
      }
    });
    onUnmounted(() => {
      if(route.params.workspace==='release'){
        cleanPackageListData();
        packageTabValueFirst.value = 'softwarescope';
        packageTabValueSecond.value = 'everything';
        showPackage.value = false;
        showList.value = false;
        defaultMilestoneId.value = null;
      }
    });
    watch([additionFeatureSummary, inheritFeatureSummary], () => {
      setFeatureOption(additionFeatureOption, '新增特性', additionFeatureSummary.value);
      setFeatureOption(inheritFeatureOption, '继承特性', inheritFeatureSummary.value);
    });
    return {
      ...modules,
      additionFeatureOption,
      inheritFeatureOption,
      detail,
      done,
      list,
      hasQualityboard,
      currentId,
      productId,
      productLoading,
      productOptions,
      productList,
      currentProduct,
      roundOptions,
      roundLoading,
      showRoundMilestoneBoard,
      showChecklistBoard,
      currentPanelDetail,
      showAddNewCompare,
      checklistBoardTableLoading,
      checklistBoardTablePagination,
      checklistBoardTableData,
      currentResolvedPassed,
      productVersionPagination,
      currentRound,
      currentAllCnt,
      showList,
      showPackage,
      currentResolvedCnt,
      currentResolvedRate,
      currentPanel,
      defaultMilestoneId,
      issuesResolvedPassed,
      leftIssuesPassed,
      leftIssuesCnt,
      packageChangeSummary,
      mainResolvedRate,
      mainResolvedPassed,
      roundCompareeId,
      requestCard,
      seriousMainResolvedPassed,
      seriousResolvedRate,
      seriousMainResolvedCnt,
      seriousMainResolvedRate,
      seriousResolvedPassed,
      seriousMainAllCnt,
      resolvedMilestoneOptions,
      resolvedMilestone,
      oldPackage,
      newPackage,
      dashboardId,
      roundIdOptions,
      roundId,
      activeTab,
      active,
      loadingRef,
      checklistBoardTableColumns,
      branchOptions,
      branch,
      newCompareForm,
      packageCompareClosable,
      packageComparePanels,
      packageTabValueFirst,
      packageTabValueSecond,
      hasMultiVersionPackage,
      additionFeatureSummary,
      inheritFeatureSummary,
      FileExport,
      boxWidth,
      MilestoneIssuesCardType,
      refreshTableData,
      changePackageTabFirst,
      changePackageTabSecond,
      handleNewCompareCreate,
      handlePackageCompareAdd,
      handlePackageCompareClose,
      getBranchSelectList,
      stepAdd,
      haveRecovery,
      handleRollback,
      handleClick,
      haveDone,
      handleChecklistBoard,
      handleMilestone,
      updateRoundMilestoneBoard,
      checklistBoardTablePageSizeChange,
      getPackageListComparationSummary,
      checklistBoardTablePageChange,
      selectResolvedMilestone,
      handleListClick,
      handlePackageCardClick,
      selectRound,
      showDailyBuildModal,
      exportQualityHistoryFn,
      getPackageChangeSummary,
      // ...productModules,
    };
  }
});
</script>

<style lang="less" scoped>
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

#drawer-target {
  .searchButtonBox {
    display: flex;
    justify-content: space-evenly;

    .btn {
      width: 100px;
    }
  }
}

.drawer-content {
  height: 100%;
  padding: 0 10px;

  .card {
    cursor: pointer;
    position: relative;
    display: flex;
    box-shadow: 0 2px 8px 0 rgb(2 24 42 / 10%);
    height: 450px;
    align-items: center;

    .topselect {
      position: absolute;
      top: 25px;
      left: 10px;
    }

    .featureProgress {
      height: 220px;
      width: 50%;
    }

    .topProgress {
      position: absolute;
      width: 190px;
      left: 15%;
      top: 15%;
    }

    .chart {
      width: 100px;
      flex-shrink: 0;
    }

    .description {
      width: 100%;
      word-break: break-word;
    }
  }
}

.transitionBox {
  cursor: pointer;

  .package-middle {
    margin: 23px 43px;
  }
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

.packageCard {
  display: flex;
  justify-content: space-evenly;
  text-align: center;
  align-items: center;
  width: 100%;
}
</style>
