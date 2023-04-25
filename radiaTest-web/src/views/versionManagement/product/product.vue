<template>
  <div>
    <modal-card
      title="注册产品版本"
      url="/v1/product"
      ref="createModalRef"
      @validate="() => createFormRef.handlePropsButtonClick()"
      @submit="createFormRef.post()"
    >
      <template #form>
        <product-create-form
          ref="createFormRef"
          @valid="() => createModalRef.submitCreateForm()"
          @close="
            () => {
              createModalRef.close();
            }
          "
        />
      </template>
    </modal-card>
    <div class="product-head">
      <div>
        <create-button title="注册产品版本" @click="createModalRef.show()" />
      </div>
      <div style="display: flex; align-items: center">
        <filterButton :filterRule="filterRule" @filterchange="filterchange" style="display: flex; padding-right: 20px">
        </filterButton>
        <refresh-button @refresh="refreshTableData"> 刷新产品版本列表 </refresh-button>
      </div>
    </div>
    <div>
      <n-data-table
        remote
        :loading="tableLoading"
        :columns="columns"
        :data="tableData"
        :pagination="productVersionPagination"
        @update:page="productVersionPageChange"
        @update:page-size="productVersionPageSizeChange"
        :row-props="rowProps"
      />
    </div>
    <!-- 产品版本抽屉 -->
    <n-drawer v-model:show="drawerShow" @after-leave="leaveProductDrawer" style="width: 60%">
      <n-drawer-content id="drawer-target">
        <template #header>
          <div style="display: flex; align-items: center">
            <n-button
              @click="
                () => {
                  drawerShow = false;
                }
              "
              style="margin-right: 20px"
              size="medium"
              quaternary
              circle
            >
              <n-icon :size="26">
                <arrow-left />
              </n-icon>
            </n-button>
            <n-h3 style="margin: 0; padding: 0">
              {{ `${detail.name}-${detail.version}` }}
            </n-h3>
          </div>
        </template>
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
          <n-grid x-gap="12" :cols="2" v-if="list.length">
            <!-- 问题解决统计 -->
            <n-gi :span="1" v-if="!showPackage && !showList">
              <div
                class="card inout-animated"
                @click="cardClick"
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
                  class="topProgress"
                  type="circle"
                  :status="
                    currentResolvedPassed !== true ? (currentResolvedPassed === false ? 'error' : 'default') : 'success'
                  "
                  :stroke-width="9"
                  :percentage="currentResolvedRate"
                >
                  <span style="text-align: center; font-size: 33px">
                    {{ currentResolvedRate ? `${currentResolvedRate}%` : '0%' }}
                  </span>
                </n-progress>
                <div style="display: flex; position: absolute; top: 4%; left: 73%">
                  <n-icon size="20" style="margin-right: 5px">
                    <CheckCircleFilled color="#18A058" v-if="issuesResolvedPassed" />
                    <QuestionCircle16Filled v-else-if="issuesResolvedPassed === null" />
                    <CancelRound color="#D03050" v-else />
                  </n-icon>
                  <span>
                    {{ issuesResolvedPassed !== null ? (issuesResolvedPassed ? '已达标' : '未达标') : 'unknown' }}
                  </span>
                </div>
                <div style="position: absolute; left: 61%; top: 16%; text-align: center">
                  <span style="font-size: 20px"> 问题解决统计 </span><br />
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
                  style="position: absolute; width: 78%; top: 80%; left: 11%"
                  type="line"
                  :status="
                    seriousMainResolvedPassed !== true
                      ? seriousMainResolvedPassed === false
                        ? 'error'
                        : 'default'
                      : 'success'
                  "
                  :indicator-placement="'inside'"
                  :percentage="seriousMainResolvedRate"
                  :height="20"
                  :border-radius="4"
                  :fill-border-radius="0"
                  processing
                />
                <n-tooltip>
                  <template #trigger>
                    <n-progress
                      :status="
                        seriousResolvedPassed !== true
                          ? seriousResolvedPassed === false
                            ? 'error'
                            : 'default'
                          : 'success'
                      "
                      style="position: absolute; width: 78%; top: 86%; left: 11%"
                      type="line"
                      :percentage="seriousResolvedRate"
                    />
                  </template>
                  严重问题解决率{{ seriousResolvedRate }}%
                </n-tooltip>
                <n-tooltip>
                  <template #trigger>
                    <n-progress
                      :status="
                        mainResolvedPassed !== true ? (mainResolvedPassed === false ? 'error' : 'default') : 'success'
                      "
                      style="position: absolute; width: 78%; top: 91%; left: 11%"
                      type="line"
                      :percentage="mainResolvedRate"
                    />
                  </template>
                  主要问题解决率{{ mainResolvedRate }}%
                </n-tooltip>
              </div>
            </n-gi>
            <n-gi :span="showList || showPackage ? 2 : 1" ref="requestCard">
              <!-- 特性 -->
              <div
                class="transitionBox"
                v-if="!showPackage"
                :style="{
                  width: showList === false ? '100%' : boxWidth + 'px'
                }"
              >
                <div
                  style="display: flex; justify-content: space-evenly; height: 100%; background: white"
                  @click="handleListClick"
                  class="card"
                  v-if="!showList"
                >
                  <div class="featureProgress">
                    <echart :option="additionFeatureOption" chartId="additionFeaturePieChart" />
                  </div>
                  <div class="featureProgress">
                    <echart :option="inheritFeatureOption" chartId="inheritFeaturePieChart" />
                  </div>
                </div>
                <div v-if="showList">
                  <n-card style="height: auto; box-shadow: 0 2px 8px 0 rgb(2 24 42 / 10%)">
                    <template #header>
                      <span>新增/继承特性测试任务跟踪</span>
                    </template>
                    <template #header-extra>
                      <n-icon @click="showList = false" style="cursor: pointer">
                        <MdClose />
                      </n-icon>
                    </template>
                    <n-tabs type="line" animated>
                      <n-tab-pane name="addition" tab="新增测试需求">
                        <feature-table type="addition" :qualityboard-id="dashboardId" />
                      </n-tab-pane>
                      <n-tab-pane name="inherit" tab="继承测试需求">
                        <feature-table type="inherit" :qualityboard-id="dashboardId" />
                      </n-tab-pane>
                    </n-tabs>
                  </n-card>
                </div>
              </div>
              <!-- 软件包 -->
              <n-card
                class="cardbox inout-animated"
                v-if="!showList"
                :style="{
                  height: showPackage ? 'auto' : ''
                }"
                :bordered="false"
                title="软件包变更"
              >
                <template #header-extra v-if="showPackage">
                  <n-icon @click="showPackage = false" style="cursor: pointer">
                    <MdClose />
                  </n-icon>
                </template>
                <template #header-extra v-else>
                  <refresh-button
                    :size="24"
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
                    style="display: flex; justify-content: space-around; height: 100%"
                    @click="handlePackageCardClick"
                    v-if="!showPackage"
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
                        <n-icon size="20" color="green">
                          <DoubleArrowFilled />
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
                      animated
                      addable
                      type="card"
                      :closable="packageCompareClosable"
                      @close="handlePackageCompareClose"
                      @add="handlePackageCompareAdd"
                    >
                      <n-tab-pane
                        v-for="packageComparePanel in packageComparePanels"
                        :key="packageComparePanel"
                        :tab="`对比${packageComparePanel.name}`"
                        :name="packageComparePanel.id"
                      >
                        <n-tabs
                          animated
                          type="line"
                          v-model:value="packageTabValueFirst"
                          @update:value="changePackageTabFirst"
                        >
                          <n-tab name="softwarescope"> 软件范围 </n-tab>
                          <n-tab v-if="currentPanel === 'fixed'" name="homonymousIsomerism"> 同名异构 </n-tab>
                        </n-tabs>
                        <n-tabs
                          animated
                          type="line"
                          v-model:value="packageTabValueSecond"
                          @update:value="changePackageTabSecond"
                        >
                          <n-tab name="everything"> everything </n-tab>
                          <n-tab name="EPOL"> EPOL </n-tab>
                        </n-tabs>
                        <div class="packageCard" v-show="packageTabValueFirst !== 'homonymousIsomerism'">
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
                              <DoubleArrowFilled />
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
                          :qualityboard-id="dashboardId"
                          :roundCompareeId="roundCompareeId"
                          :round-cur-id="currentId"
                          :packageTabValueFirst="packageTabValueFirst"
                          :packageTabValueSecond="packageTabValueSecond"
                          :hasMultiVersionPackage="hasMultiVersionPackage"
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
                              filterable
                              v-model:value="newCompareForm.product"
                              :options="productOptions"
                              :loading="productLoading"
                              placeholder="请选择比对的基线版本"
                            />
                          </n-form-item>
                          <n-radio-group v-model:value="newCompareForm.type">
                            <n-space>
                              <n-radio value="release"> 发布版本 </n-radio>
                              <n-radio value="round"> 迭代轮次 </n-radio>
                            </n-space>
                          </n-radio-group>
                          <n-form-item path="round">
                            <n-select
                              filterable
                              v-model:value="newCompareForm.round"
                              :options="roundOptions"
                              :loading="roundLoading"
                            />
                          </n-form-item>
                        </n-form>
                      </div>
                      <template #action>
                        <n-button type="primary" @click="handleNewCompareCreate"> 提交 </n-button>
                      </template>
                    </n-modal>
                  </div>
                </div>
              </n-card>
            </n-gi>
            <n-gi :span="2" style="margin-top: 40px">
              <n-tabs type="line" animated v-model:value="activeTab">
                <n-tab-pane tab="测试进展" name="testProgress"> </n-tab-pane>
                <n-tab-pane tab="质量防护网" name="qualityProtect"> </n-tab-pane>
                <n-tab-pane :disabled="true" name="performance" tab="性能看板"> </n-tab-pane>
                <n-tab-pane :disabled="true" name="compatibility" tab="兼容性看板"> </n-tab-pane>
              </n-tabs>
              <div>
                <keep-alive>
                  <test-progress v-if="activeTab === 'testProgress'" :defaultMilestoneId="defaultMilestoneId" />
                  <quality-protect v-else-if="activeTab === 'qualityProtect'" :quality-board-id="dashboardId" />
                </keep-alive>
              </div>
            </n-gi>
          </n-grid>
          <n-empty
            size="huge"
            style="justify-content: center; height: 100%"
            description="未通过质量checklist，无法开启第一轮迭代测试"
            v-else
          />
          <!-- issue 弹窗 -->
          <n-drawer
            v-model:show="active"
            placement="right"
            :mask-closable="false"
            :trap-focus="false"
            height="100%"
            width="95%"
          >
            <n-drawer-content closable>
              <MilestoneIssuesCard :milestone-id="resolvedMilestone.id" :cardType="MilestoneIssuesCardType" />
            </n-drawer-content>
          </n-drawer>
        </div>
        <n-modal v-model:show="showChecklistBoard">
          <n-card
            style="width: 1000px"
            title="检查项比对结果"
            :bordered="false"
            size="huge"
            role="dialog"
            aria-modal="true"
          >
            <n-data-table
              :loading="checklistBoardTableLoading"
              :columns="checklistBoardTableColumns"
              :data="checklistBoardTableData"
              :pagination="checklistBoardTablePagination"
              @update:page="checklistBoardTablePageChange"
              @update:page-size="checklistBoardTablePageSizeChange"
            />
          </n-card>
        </n-modal>
        <n-modal v-model:show="showRoundMilestoneBoard" @update:show="updateRoundMilestoneBoard">
          <RoundRelateMilestones :ProductId="ProductId" :currentRound="currentRound"></RoundRelateMilestones>
        </n-modal>
      </n-drawer-content>
    </n-drawer>
    <n-modal v-model:show="showCheckList">
      <n-card
        style="width: 1000px"
        :title="checkListModalTitle"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
        class="checkListWrap"
      >
        <div class="addBtn">
          <n-button class="btn" type="info" @click="addCheckItem"> 新增检查项 </n-button>
          <n-button class="btn" type="info" @click="addBaseline"> 变更基准值 </n-button>
        </div>
        <div>
          <n-data-table
            :loading="checkListTableLoading"
            :columns="checkListTableColumns"
            :data="checkListTableData"
            :pagination="checkListTablePagination"
            @update:page="checkListTablePageChange"
            @update:page-size="checkListTablePageSizeChange"
          />
        </div>
      </n-card>
    </n-modal>
    <n-drawer
      v-model:show="showCheckListDrawer"
      :maskClosable="false"
      width="324px"
      placement="right"
      class="checkListDrawer"
    >
      <n-drawer-content :title="isAddBaseline ? '变更基准值' : '新增检查项'">
        <n-form
          :model="checkListDrawerModel"
          :rules="checkListDrawerRules"
          ref="checkListDrawerFormRef"
          label-placement="left"
          :label-width="80"
          size="medium"
          :style="{}"
        >
          <n-form-item label="产品名称" path="product_id">
            <n-select
              v-model:value="checkListDrawerModel.product_id"
              placeholder="请选择产品名称"
              :options="productList"
              disabled
            />
          </n-form-item>
          <n-form-item label="检查项" path="checkitem_id">
            <n-select
              v-model:value="checkListDrawerModel.checkitem_id"
              placeholder="请选择检查项"
              :options="isAddBaseline ? existedCheckItemList : checkItemList"
              filterable
            />
          </n-form-item>
          <n-form-item label="基准值" path="baseline" first>
            <n-input placeholder="请输入基准值" v-model:value="checkListDrawerModel.baseline" />
          </n-form-item>
          <n-form-item label="运算符" path="operation">
            <n-select
              v-model:value="checkListDrawerModel.operation"
              placeholder="请选择运算符"
              :options="operationOptions"
            />
          </n-form-item>
          <n-form-item label="Rounds" path="rounds" v-if="isAddBaseline">
            <n-select
              multiple
              v-model:value="checkListDrawerModel.rounds"
              placeholder="请选择迭代版本"
              :options="roundsOptions"
            />
          </n-form-item>
          <div class="buttonWrap">
            <n-button class="btn" type="error" ghost @click="cancelCheckListDrawer">取消</n-button>
            <n-button v-show="!isAddBaseline" class="btn" type="info" ghost @click="confirmCheckItem">新增</n-button>
            <n-button v-show="isAddBaseline" class="btn" type="info" ghost @click="confirmBaseline">确定</n-button>
          </div>
        </n-form>
      </n-drawer-content>
    </n-drawer>
    <n-modal v-model:show="showEditProductVersionModal" class="editProductVersionWrap">
      <n-card style="width: 600px" title="编辑产品信息" :bordered="false" size="huge" role="dialog" aria-modal="true">
        <n-form ref="productVersionFormRef" :model="productVersionModel">
          <n-form-item path="name" label="产品">
            <n-input v-model:value="productVersionModel.name" @keydown.enter.prevent />
          </n-form-item>
          <n-form-item path="version" label="版本">
            <n-input v-model:value="productVersionModel.version" @keydown.enter.prevent />
          </n-form-item>
          <n-form-item path="description" label="描述">
            <n-input v-model:value="productVersionModel.description" @keydown.enter.prevent />
          </n-form-item>
          <n-form-item path="start_time" label="开始时间">
            <n-date-picker v-model:value="productVersionModel.start_time" type="date" />
          </n-form-item>
          <n-form-item path="end_time" label="结束时间">
            <n-date-picker v-model:value="productVersionModel.end_time" type="date" />
          </n-form-item>
          <div class="buttonWrap">
            <n-button class="btn" type="error" ghost @click="cancelEditProductVersionModal">取消</n-button>
            <n-button class="btn" type="info" ghost @click="confirmEditProductVersionModal">确定</n-button>
          </div>
        </n-form>
      </n-card>
    </n-modal>
  </div>
</template>
<script>
import { getProduct } from '@/api/get';
import Common from '@/components/CRUD';
import Essential from '@/components/productComponents';
import { Search } from '@vicons/carbon';
import { modules } from './modules';
import { ArrowLeft32Filled as ArrowLeft, QuestionCircle16Filled } from '@vicons/fluent';
import { MdClose } from '@vicons/ionicons4';
import { DoubleArrowFilled, CancelRound, CheckCircleFilled } from '@vicons/material';
import autoSteps from '@/components/autoSteps/autoSteps.vue';
import MilestoneIssuesCard from '@/components/milestoneComponents/MilestoneIssuesCard.vue';
import testProgress from '@/components/productDrawer/testProgress.vue';
import qualityProtect from '@/components/productDrawer/qualityProtect.vue';
import FeatureTable from '@/components/productDrawer/FeatureTable.vue';
import filterButton from '@/components/filter/filterButton.vue';
import PackageTable from '@/components/productDrawer/PackageTable.vue';
import RefreshButton from '@/components/CRUD/RefreshButton';
import { getProductVersionOpts } from '@/assets/utils/getOpts';
import echart from '@/components/echart/echart.vue';

export default {
  components: {
    ...Common,
    ...Essential,
    filterButton,
    ArrowLeft,
    autoSteps,
    MilestoneIssuesCard,
    testProgress,
    MdClose,
    RefreshButton,
    DoubleArrowFilled,
    CancelRound,
    CheckCircleFilled,
    qualityProtect,
    QuestionCircle16Filled,
    FeatureTable,
    PackageTable,
    echart
  },
  setup() {
    const additionFeatureOption = reactive(JSON.parse(JSON.stringify(modules.featureOption)));
    const inheritFeatureOption = reactive(JSON.parse(JSON.stringify(modules.featureOption)));
    const refreshTableData = () => {
      modules.getTableData({
        page_num: 1,
        page_size: modules.productVersionPagination.value.pageSize
      });
    };
    onMounted(() => {
      modules.getTableData({
        page_num: modules.productVersionPagination.value.page,
        page_size: modules.productVersionPagination.value.pageSize
      });
      getProductVersionOpts(modules.productList);
      modules.setFeatureOption(additionFeatureOption, '新增特性', modules.additionFeatureSummary.value);
      modules.setFeatureOption(inheritFeatureOption, '继承特性', modules.inheritFeatureSummary.value);
    });
    watch([modules.additionFeatureSummary, modules.inheritFeatureSummary], () => {
      modules.setFeatureOption(additionFeatureOption, '新增特性', modules.additionFeatureSummary.value);
      modules.setFeatureOption(inheritFeatureOption, '继承特性', modules.inheritFeatureSummary.value);
    });
    onUnmounted(() => {
      modules.cleanPackageListData();
    });
    return {
      createFormRef: ref(),
      createModalRef: ref(),
      getProduct,
      Search,
      ...modules,
      inheritFeatureOption,
      additionFeatureOption,
      refreshTableData
    };
  }
};
</script>

<style>
.resolvedRate {
  width: 140px;
}

.seriousMain {
  width: 160px;
}
</style>

<style lang="less" scoped>
.product-head {
  display: flex;
  justify-content: space-between;
  margin: 10px 0;
}

.transitionBox {
  cursor: pointer;
  .package-middle {
    margin: 23px 43px;
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

.packageCard {
  display: flex;
  justify-content: space-evenly;
  text-align: center;
  align-items: center;
  width: 100%;
}

.cardbox {
  margin: 9px 0 0 0;
  padding: 0;
  height: 220px;
  box-shadow: 0 2px 8px 0 rgb(2 24 42 / 10%);
}
.inout-animated {
  --animate-duration: 0.3s;
}

.checkListWrap {
  .addBtn {
    display: flex;
    justify-content: right;
    margin-bottom: 15px;

    .btn {
      margin: 0 5px;
    }
  }
}

.checkListDrawer {
  .buttonWrap {
    display: flex;
    justify-content: space-evenly;
    .btn {
      width: 100px;
    }
  }
}

.editProductVersionWrap {
  .buttonWrap {
    display: flex;
    justify-content: center;
    .btn {
      margin: 0 10px;
      width: 100px;
    }
  }
}
</style>
