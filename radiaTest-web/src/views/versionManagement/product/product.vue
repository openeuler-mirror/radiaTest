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
    <n-drawer v-model:show="drawerShow" :width="800">
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
            <n-gi v-for="(item, index) in cardInfo" :key="item.id">
              <div class="card" @click="cardClick(index)">
                <n-progress
                  type="dashboard"
                  gap-position="bottom"
                  :percentage="item.progress"
                />
                <div class="description">
                  {{ item.description }}
                </div>
              </div>
            </n-gi>
            <n-gi :span="3">
              <autoSteps @stepClick="handleClick" :list="list" />
            </n-gi>
            <n-gi
              v-show="!showPackage"
              :span="showList ? 3 : 2"
              ref="requestCard"
            >
              <div
                class="transitionBox"
                :style="{
                  width: showList === undefined ? '100%' : boxWidth + 'px',
                }"
              >
                <div
                  style="display:flex;justify-content:space-around;height:100%;"
                  @click="showList = true"
                  class="card"
                  v-show="!showList"
                >
                  <div style="text-align:center">
                    <p>
                      新增需求<span>{{ newRequestCount }}</span>
                    </p>
                    <n-progress
                      type="dashboard"
                      gap-position="bottom"
                      :percentage="newRequestRate"
                    />
                    <p class="description">
                      通过率
                    </p>
                  </div>
                  <n-divider vertical style="height:100%" />
                  <div style="text-align:center">
                    <p>
                      继承需求<span>{{ extendRequestCount }}</span>
                    </p>
                    <n-progress
                      type="dashboard"
                      gap-position="bottom"
                      :percentage="extendRequestRate"
                    />
                    <p class="description">
                      通过率
                    </p>
                  </div>
                </div>
                <div v-show="showList">
                  <n-card>
                    <template #header>
                      <n-tabs type="line" animated>
                        <n-tab-pane name="new" tab="新增需求"> </n-tab-pane>
                        <n-tab-pane name="extend" tab="继承需求"> </n-tab-pane>
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
            </n-gi>
            <n-gi
              :span="showPackage ? 3 : 1"
              v-show="!showList"
              ref="packageBox"
            >
              <n-card
                class="cardbox"
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
                    @click="showPackage = true"
                    v-show="!showPackage"
                  >
                    <div class="packageCard transitionBox">
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
                  </div>
                  <div v-show="showPackage">
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
            <n-gi :span="3">
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
                    :treeList="testProgressList"
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
              <p>遗留问题解决率</p>
              <n-progress
                type="line"
                :percentage="60"
                :indicator-placement="'inside'"
                processing
              />
              <MilestoneIssuesCard />
            </n-drawer-content>
          </n-drawer>
        </div>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>
<script>
import { ref } from 'vue';
import Common from '@/components/CRUD';
import Essential from '@/components/productComponents';
import { Search } from '@vicons/carbon';
import { modules } from './modules';
import { ArrowLeft32Filled as ArrowLeft } from '@vicons/fluent';
import { MdClose } from '@vicons/ionicons4';
import { DoubleArrowFilled } from '@vicons/material';
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
    qualityProtect,
  },
  data() {
    return {
      list: [
        { key: 1, text: 111, success: false },
        { key: 2, text: 222, success: false },
      ],
    };
  },
  setup() {
    modules.getTableData();
    return {
      createFormRef: ref(),
      createModalRef: ref(),
      Search,
      ...modules,
    };
  },
  methods: {
    handleClick(index) {
      this.list[index].success = !this.list[index].success;
    },
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
  transition: all 0.5s;
}
.drawer-content {
  padding: 0 10px;
  .card {
    display: flex;
    box-shadow: 0 2px 8px 0 rgb(2 24 42 / 10%);
    height: 150px;
    align-items: center;
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
  margin:0;
  padding:0;
  height:220px;
  box-shadow: 0 2px 8px 0 rgb(2 24 42 / 10%);
}
</style>
