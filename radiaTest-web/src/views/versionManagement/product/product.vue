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
      <div style="display:flex;width:100%">
        <create-button title="注册产品版本" @click="createModalRef.show()" />
        <n-input
          style="max-width:500px"
          v-model:value="searchInfo"
          round
          placeholder="搜索"
          size="large"
        >
          <template #suffix>
            <n-icon :component="Search" />
          </template>
        </n-input>
      </div>
      <n-icon size="35" style="right: 10px;cursor: pointer;" @click="showCheckList = true">
        <MdMenu />
      </n-icon>
      <n-select
        placeholder="请选择产品"
        style="width:200px"
        :options="productList"
      />
    </div>
    <div>
      <n-data-table
        :loading="tableLoading"
        :columns="columns"
        :data="tableData"
        :row-props="rowProps"
      />
    </div>
    <n-drawer v-model:show="drawerShow" :width="950">
      <n-drawer-content id="drawer-target">
        <template #header>
          <div style="display:flex;align-items:center">
            <n-button
              @click="
                () => {
                  drawerShow = false;
                }
              "
              style="margin-right:20px"
              size="medium"
              quaternary
              circle
            >
              <n-icon :size="26">
                <arrow-left />
              </n-icon>
            </n-button>
            <n-h3 style="margin:0;padding:0">
              {{ `${detail.name}-${detail.version}` }}
            </n-h3>
          </div>
        </template>
        <div class="drawer-content">
          <n-grid x-gap="12" :cols="3">
            <n-gi :span="5" style="display: flex;margin-top: 15px;cursor: pointer;align-items: center;" @click="cardClick">
              <div style="width: 150px;margin-right: 10px;">
                <span>遗留问题解决率</span><br/>
                <span style="color: #DAE0E8;width: 135px;text-align: center;margin-left: 22px;">前置版本</span>
              </div>
              <n-progress
                type="line"
                status="success"
                :percentage="90"
                :height="20"
                :border-radius="4"
                :fill-border-radius="0"
                processing
              />
              <span style="width: 60px;">转测</span>
              <div style="width: 145px;">
                <span>遗留问题数:</span>
                <span style="text-align: center;margin-left: 10px;">{{ leftIssuesCnt }}</span><br/>
                <span style="color: #DAE0E8;margin-left: 22px;">前置迭代</span>
              </div>
            </n-gi>
            <n-gi :span="3" style="margin-top: 40px;margin-bottom: 20px;">
              <autoSteps @stepClick="handleClick" @haveDone="haveDone" @haveRecovery="haveRecovery" @add="stepAdd" @releaseclick="releaseclick" :addTip="addmessage" :done="done" :list="list" :currentId="currentId" />
            </n-gi>
          </n-grid>
          <n-grid x-gap="12" :cols="2">
            <n-gi :span="1" v-show="!showPackage && !showList">
              <div class="card" @click="cardClick" :style="{backgroundColor:currentSovledRate >= 70?'#D5E8D4':'#F8CECC',border:currentSovledRate >= 70?'1px solid #A2C790':'1px solid #B95854'}">
                <n-progress
                  style="width:190px;position:absolute;left:35px;"
                  class="topProgress"
                  type="circle"
                  :status="currentSovledRate >= 70 ? 'success' : 'error'"
                  stroke-width="9"
                  :percentage="currentSovledRate"
                >
                  <span style="text-align: center;font-size: 33px;">{{ currentSovledRate + '%' }}</span>
                </n-progress>
                <div style="display: flex;position: absolute;top: 4%;left: 73%;">
                  <n-icon size="20" style="margin-right: 5px;">
                    <CheckCircleFilled color="#18A058" v-if="currentSovledRate >= 70" />
                    <CancelRound color="#D03050" v-else />
                  </n-icon>
                  <span v-if="list.length < 5 && !done">下一轮迭代</span>
                  <span v-else>发布</span>
                </div>
                <div style="position:absolute;left: 61%;top: 24%;text-align: center;">
                  <span style="font-size: 20px;">当前里程碑</span><br><span style="font-size: 20px;">问题解决统计</span>
                  <p style="font-size: 30px;margin-top: 3px;">{{`${currentSovledCnt}/${currentAllCnt}`}}</p>
                </div>
                <div class="description" style="font-size: 19px;position:absolute;top:69%;display:flex;justify-content:space-around;">
                  <span>严重/主要问题解决率</span>
                  <span>{{ `${seriousMainSolvedCnt}/${seriousMainAllCnt}` }}</span>
                </div>
                <n-progress
                  style="position: absolute;width: 78%;top: 80%;left: 11%;"
                  type="line"
                  status="error"
                  :indicator-placement="'inside'"
                  :percentage="seriousMainSolvedRate"
                  :height="20"
                  :border-radius="4"
                  :fill-border-radius="0"
                  processing
                />
                <n-progress style="position: absolute;width: 78%;top: 86%;left: 11%;" type="line" :percentage="seriousSovledRate" />
                <n-progress style="position: absolute;width: 78%;top: 91%;left: 11%;" type="line" :percentage="mainSolvedRate" />
              </div>
            </n-gi>
            <n-gi
              :span="showList || showPackage? 2 : 1"
              ref="requestCard"
            >
              <div
                class="transitionBox"
                v-show="!showPackage"
                :style="{
                  width: showList === false ? '100%' : boxWidth + 'px',
                }"
              >
                <div
                  style="display:flex;justify-content:space-around;height:100%;"
                  @click="
                    () => {
                      showList = true;
                    }
                  "
                  class="card"
                  v-show="!showList"
                >
                  <div style="text-align:center">
                    <p>
                      新增测试需求: <span>{{ newRequestCount }}</span>
                    </p>
                    <n-progress
                      type="dashboard"
                      gap-position="bottom"
                      :percentage="newRequestRate"
                    />
                    <p class="description">
                      完成度
                    </p>
                  </div>
                  <n-divider vertical style="height:100%" />
                  <div style="text-align:center">
                    <p>
                      继承测试需求: <span>{{ extendRequestCount }}</span>
                    </p>
                    <n-progress
                      type="dashboard"
                      gap-position="bottom"
                      :percentage="extendRequestRate"
                    />
                    <p class="description">
                      完成度
                    </p>
                  </div>
                </div>
                <div v-show="showList">
                  <n-card style="height: auto;box-shadow: 0 2px 8px 0 rgb(2 24 42 / 10%);">
                    <template #header>
                      <n-tabs type="line" animated>
                        <n-tab-pane name="new" tab="新增测试需求"> </n-tab-pane>
                        <n-tab-pane name="extend" tab="继承测试需求"> </n-tab-pane>
                      </n-tabs>
                    </template>
                    <template #header-extra>
                      <n-icon @click="showList = false" style="cursor:pointer">
                        <MdClose />
                      </n-icon>
                    </template>
                    <n-data-table />
                  </n-card>
                </div>
              </div>
              <n-card
                class="cardbox"
                v-show="!showList"
                :style="{height:showPackage?'auto':''}"
                :bordered="false"
                title="软件包变更"
              >
                <template #header-extra v-if="showPackage">
                  <n-icon @click="showPackage = false" style="cursor:pointer">
                    <MdClose />
                  </n-icon>
                </template>
                <div
                  class="transitionBox"
                  :style="{
                    width:
                      showPackage === false ? '100%' : packageWidth + 'px',
                  }"
                >
                  <div
                    style="display:flex;justify-content:space-around;height:100%;"
                    @click="
                      () => {
                        showPackage = true;
                      }
                    "
                    v-show="!showPackage"
                  >
                    <div class="packageCard transitionBox">
                      <div class="package-left">
                        <n-h3 style="font-size: 33px;">
                          {{ oldPackage.size }}
                        </n-h3>
                        <p>{{ oldPackage.name }}</p>
                      </div>
                      <div class="package-middle">
                        <p style="font-size: 15px;">+{{ newPackage.size - oldPackage.size }}</p>
                        <n-icon size="20" color="green">
                          <DoubleArrowFilled />
                        </n-icon>
                      </div>
                      <div class="package-right">
                        <n-h3 style="font-size: 33px;">
                          {{ newPackage.size }}
                        </n-h3>
                        <p>{{ newPackage.name }}</p>
                      </div>
                    </div>
                  </div>
                  <div v-show="showPackage" style="width: 826px;">
                    <div class="packageCard">
                      <div class="package-left">
                        <n-h3>
                          {{ oldPackage.size }}
                        </n-h3>
                        <p>{{ oldPackage.name }}</p>
                      </div>
                      <div class="package-middle">
                        <p>+{{ newPackage.size - oldPackage.size }}</p>
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
                    <n-data-table />
                  </div>
                </div>
              </n-card>
            </n-gi>
            <n-gi :span="2" style="margin-top: 40px;">
              <n-tabs type="line" animated v-model:value="activeTab">
                <n-tab-pane tab="测试进展" name="testProgress"> </n-tab-pane>
                <n-tab-pane tab="质量防护网" name="qualityProtect">
                </n-tab-pane>
                <n-tab-pane name="performance" tab="性能看板"> </n-tab-pane>
                <n-tab-pane name="compatibility" tab="兼容性看板"> </n-tab-pane>
              </n-tabs>
              <div>
                <keep-alive>
                  <test-progress
                    v-if="activeTab === 'testProgress'"
                    :treeList="testList"
                  />
                  <quality-protect
                    v-else-if="activeTab === 'qualityProtect'"
                    :treeList="testProgressList"
                  />
                </keep-alive>
              </div>
            </n-gi>
          </n-grid>
          <n-drawer
            v-model:show="active"
            placement="bottom"
            :mask-closable="false"
            :trap-focus="false"
            to="#drawer-target"
            height="100%"
          >
            <n-drawer-content closable>
              <MilestoneIssuesCard />
            </n-drawer-content>
          </n-drawer>
        </div>
      </n-drawer-content>
    </n-drawer>
    <n-modal v-model:show="showCheckList">
      <n-card
        style="width: 600px"
        title="checkList信息"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
      >
      </n-card>
    </n-modal>
    <n-modal v-model:show="showModal">
      <n-card
        style="width: 600px"
        title="编辑产品信息"
        :bordered="false"
        size="huge"
        role="dialog"
        aria-modal="true"
      >
        <n-form ref="formRef" :model="model">
          <n-form-item path="name" label="产品">
            <n-input v-model:value="model.name" @keydown.enter.prevent />
          </n-form-item>
          <n-form-item path="version" label="版本">
            <n-input v-model:value="model.version" @keydown.enter.prevent />
          </n-form-item>
          <n-form-item path="start_time" label="开始时间">
            <n-input v-model:value="model.start_time" @keydown.enter.prevent />
          </n-form-item>
          <n-form-item path="end_time" label="结束时间">
            <n-input v-model:value="model.end_time" @keydown.enter.prevent />
          </n-form-item>
          <n-form-item path="public_time" label="发布时间">
            <n-input v-model:value="model.public_time" @keydown.enter.prevent />
          </n-form-item>
          <n-form-item path="bequeath" label="遗留解决">
            <n-input v-model:value="model.bequeath" @keydown.enter.prevent />
          </n-form-item>
          <n-row :gutter="[0, 24]">
            <n-col :span="24">
              <div style="display: flex; justify-content: flex-end">
                <n-button
                  :disabled="model.age === null"
                  round
                  type="primary"
                  @click="handleValidateButtonClick"
                >
                  确定
                </n-button>
              </div>
            </n-col>
          </n-row>
        </n-form>
      </n-card>
  </n-modal>
  </div>
</template>
<script>
import { ref, onMounted } from 'vue';
import Common from '@/components/CRUD';
import Essential from '@/components/productComponents';
import { Search } from '@vicons/carbon';
import { modules } from './modules';
import { ArrowLeft32Filled as ArrowLeft } from '@vicons/fluent';
import { MdClose, MdMenu } from '@vicons/ionicons4';
import { DoubleArrowFilled, CancelRound, CheckCircleFilled } from '@vicons/material';
import autoSteps from '@/components/autoSteps/autoSteps.vue';
import MilestoneIssuesCard from '@/components/milestoneComponents/MilestoneIssuesCard.vue';
import testProgress from '@/components/productDrawer/testProgress.vue';
import qualityProtect from '@/components/productDrawer/qualityProtect.vue';
export default {
  components: {
    ...Common,
    ...Essential,
    ArrowLeft,
    autoSteps,
    MilestoneIssuesCard,
    testProgress,
    MdClose,
    DoubleArrowFilled,
    CancelRound,
    CheckCircleFilled,
    MdMenu,
    qualityProtect,
  },
  data() {
    return {
    };
  },
  setup() {
    onMounted(() => {
      modules.getTableData();
      modules.getDefaultList();
    });
    return {
      createFormRef: ref(),
      createModalRef: ref(),
      Search,
      ...modules,
    };
  },
};
</script>
<style lang="less" scoped>
.product-head {
  display: flex;
  justify-content: space-between;
  margin: 10px 0;
}
.transitionBox {
  cursor: pointer;
  // transition: all 0.5s;
  .package-middle{
    margin: 23px 43px;
  }
}
.drawer-content {
  padding: 0 10px;
  .card {
    cursor: pointer;
    position: relative;
    display: flex;
    box-shadow: 0 2px 8px 0 rgb(2 24 42 / 10%);
    height: 450px;
    align-items: center;
    .topProgress {
      position: absolute;
      left: 22%;
      top:15%;
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
  justify-content: space-around;
  text-align: center;
  align-items: center;
}
.cardbox{
  margin:9px 0 0 0;
  padding:0;
  height:220px;
  box-shadow: 0 2px 8px 0 rgb(2 24 42 / 10%);
}
</style>
