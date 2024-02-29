<template>
  <div class="container">
    <div class="title">
      <div class="screen-list">
        <n-grid x-gap="12" :cols="12">
          <n-gi :span="3">
            <div class="title-option">
              <span style="flex-shrink: 0">任务时间段:</span>
              <n-date-picker
                v-model:value="timeRange"
                type="daterange"
                style="width: 100%"
                :is-date-disabled="disablePreviousDate"
                clearable
              />
            </div>
          </n-gi>
          <n-gi :span="1">
            <div class="title-option">
              <span style="flex-shrink: 0">任务类别:</span>
              <n-select
                v-model:value="type"
                @update:value="
                  () => {
                    getGroup();
                    getOwner();
                  }
                "
                :options="typeOptions"
                clearable
              />
            </div>
          </n-gi>
          <n-gi :span="2">
            <div class="title-option">
              <span style="flex-shrink: 0">责任团队:</span>
              <n-select
                :disabled="type !== 'GROUP'"
                :render-label="renderLabel"
                v-model:value="group"
                multiple
                clearable
                :options="groupOptions"
              />
            </div>
          </n-gi>
          <n-gi :span="3">
            <div class="title-option">
              <span style="flex-shrink: 0">责任人:</span>
              <n-select
                :disabled="type === 'PERSON'"
                :render-label="renderLabel"
                v-model:value="owner"
                multiple
                clearable
                :options="ownerOptions"
              />
            </div>
          </n-gi>
          <n-gi :span="2">
            <div class="title-option">
              <span style="flex-shrink: 0">里程碑:</span>
              <n-select v-model:value="milestone" :options="milestoneOptions" clearable />
            </div>
          </n-gi>
          <n-gi :span="1">
            <div class="title-option">
              <n-button type="primary" @click="getStatics"> 查询 </n-button>
            </div>
          </n-gi>
        </n-grid>
      </div>
      <div class="file-list"></div>
    </div>
    <n-grid x-gap="12" :cols="2" y-gap="12">
      <n-gi class="grid-item">
        <div class="chart" style="display: flex; flex-direction: column; margin: 0 5px; padding: 0">
          <h3 style="flex-shrink: 0">任务数</h3>
          <div
            style="height: 100%; display: flex; justify-content: space-around; align-items: center"
          >
            <div class="staticData">
              <p class="static-title">未完成</p>
              <p class="static-account" style="color: rgba(0, 47, 167, 1)">
                {{ count.incomplete }}
              </p>
            </div>
            <div class="staticData">
              <p class="static-title">已完成</p>
              <p class="static-account" style="color: #ccc">
                {{ count.completed }}
              </p>
            </div>
            <div class="staticData">
              <p class="static-title">任务总数</p>
              <p class="static-account">{{ count.total }}</p>
            </div>
            <div style="display: inline-block; height: 60%">
              <div style="width: 1px; background: #ccc; height: 100%"></div>
            </div>
            <div class="staticData">
              <p class="static-title">今日到期</p>
              <p class="static-account" style="color: orange">
                {{ count.dueToday }}
              </p>
            </div>
            <div class="staticData">
              <p class="static-title">已逾期</p>
              <p class="static-account" style="color: red">
                {{ count.overdue }}
              </p>
            </div>
          </div>
        </div>
      </n-gi>
      <n-gi class="grid-item">
        <div class="chart">
          <echart :option="lineOptions" chartId="lineChart" />
        </div>
      </n-gi>
      <n-gi class="grid-item">
        <div class="chart">
          <echart :option="barOptions" chartId="barChart" />
        </div>
      </n-gi>
      <n-gi class="grid-item">
        <div class="chart">
          <echart :option="pieOption" chartId="pieChart" />
        </div>
      </n-gi>
      <n-gi class="grid-item" :span="2">
        <n-select v-model:value="stateType" @update:value="getStatics" :options="issueTypeOpts" />
        <n-data-table
          :columns="columns"
          remote
          :data="tableData"
          :pagination="pagination"
          :row-key="(row) => row.id"
          @update:filters="handleFiltersChange"
          @update:page="changePage"
          @update:page-size="changePageSize"
        />
      </n-gi>
    </n-grid>

    <n-modal
      v-model:show="previewShow"
      preset="dialog"
      :show-icon="false"
      title="Dialog"
      class="previewWindow"
      :style="{ width: previewWidth + 'px', height: previewHeight + 'px' }"
    >
      <template #header>
        <h3>{{ md.name }}</h3>
      </template>
      <div class="previewContent" :style="{ height: previewHeight - 100 + 'px' }">
        <v-md-editor
          v-model="md.content"
          :left-toolbar="tools"
          :include-level="[1, 4]"
        ></v-md-editor>
      </div>
    </n-modal>
  </div>
</template>

<script>
import echart from '@/components/echart/echart.vue';
import { modules } from './modules/index.js';

export default {
  components: {
    echart,
  },
  setup() {
    modules.getStatics();
    modules.getGroup();
    modules.getOwner();
    modules.getMilestone();
    return modules;
  },
};
</script>

<style>
.file {
  display: flex;
  width: 500px;
  justify-content: space-around;
  align-items: center;
  margin: 10px;
}
.file-name {
  padding: 5px 0;
  margin: 0;
  text-overflow: ellipsis;
  overflow: hidden;
  max-width: 60px;
}
.file:hover {
  background: #ccc;
}
.container {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px;
}
.container .title .screen-list {
  margin: 10px 0;
}
.container .title {
  max-height: 200px;
  border-bottom: 1px #ccc dashed;
  margin-bottom: 20px;
}
.container .chart {
  height: 300px;
  flex-shrink: 0;
}
.title-option {
  display: flex;
  align-items: center;
  height: 100%;
}
.container .title .file-list {
  overflow-y: auto;
}
.previewContent {
  overflow-y: auto;
}
.grid-item {
  box-shadow: 0 2px 8px 0 rgb(2 24 42 / 10%);
}
.staticData {
  width: 18%;
  display: inline-block;
  text-align: center;
}
.staticData .static-title {
  font-size: 18px;
  padding: 0;
  margin: 0;
}
.staticData .static-account {
  font-size: 60px;
  font-weight: bold;
  padding: 0;
  margin: 0;
}
</style>
