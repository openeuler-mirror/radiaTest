<template>
  <n-drawer
    v-model:show="showCaseDrawer"
    :width="fullScreen ? '100%' : 1400"
    class="caseDrawerContainer"
    @afterLeave="closeDrawerCb"
  >
    <n-drawer-content
      id="drawer-target"
      header-style="justify-content: center;"
      body-style="background-color: rgba(240,241,244,1)"
    >
      <template #header>
        <div class="header">
          <div class="header-left">
            <n-button @click="closeDrawerCb" class="backIcon" size="medium" quaternary circle>
              <n-icon :size="26">
                <arrow-left />
              </n-icon>
            </n-button>
            <span>执行：{{ caseDrawerData.name }}</span>
            <n-button
              :type="caseDrawerData.status === 0 ? 'info' : 'error'"
              ghost
              style="margin-left: 30px"
              @click="handleChangeTask(caseDrawerData.status)"
            >
              {{ caseDrawerData.status === 0 ? '结束任务' : '重新执行' }}
            </n-button>
          </div>
          <div>
            <n-tooltip trigger="hover" v-if="fullScreen">
              <template #trigger>
                <n-icon size="26" @click="() => (fullScreen = false)">
                  <full-screen />
                </n-icon>
              </template>
              缩小
            </n-tooltip>
            <n-tooltip trigger="hover" v-else>
              <template #trigger>
                <n-icon size="26" @click="() => (fullScreen = true)">
                  <small-screen />
                </n-icon>
              </template>
              全屏
            </n-tooltip>
          </div>
        </div>
      </template>
      <n-grid :cols="36" :x-gap="12" style="height: 100%; overflow: hidden">
        <n-gi :span="11" style="height: 100%; overflow: hidden; background: #fff">
          <n-scrollbar style="max-height: 100%; width: calc(100% + 20px)">
            <n-card class="caseCard">
              <n-radio-group
                name="radiogroup"
                :default-value="4"
                v-model:value="changeSelectValue"
                @update:value="handleUpdateStatus"
                size="small"
              >
                <n-space>
                  <n-radio
                    v-for="option in statusOptions"
                    :key="option.value"
                    :value="option.value"
                  >
                    {{ option.label }}
                  </n-radio>
                </n-space>
              </n-radio-group>
              <n-input
                placeholder="搜索用例"
                clearable
                @input="handleFilter"
                style="margin: 20px 0 30px 0"
              />
              <template v-for="card in caseDrawerData.cases" :key="card.id">
                <n-alert
                  class="alertButton"
                  :title="card.case_name"
                  :id="'case' + card.id"
                  :type="
                    card.result === 1
                      ? 'success'
                      : card.result === 0 && card.status === 1
                      ? 'error'
                      : card.result === 2 && card.status === 1
                      ? 'warning'
                      : 'info'
                  "
                  @click="handleSelectCase(card)"
                >
                  <template #header>
                    <n-h4 style="word-wrap: break-word">
                      {{ card.case_name }}
                    </n-h4>
                  </template>
                  状态：{{ card.status === 1 ? '已执行' : '执行中' }}
                </n-alert>
              </template>
            </n-card>
          </n-scrollbar>
        </n-gi>
        <n-gi :span="25" style="height: 100%; overflow: hidden; background: #fff">
          <n-scrollbar style="max-height: 100%">
            <n-card class="caseCard" style="min-height: 100%">
              <h2>{{ activeCaseDetail.case_name || '测试用例名' }}</h2>
              <div style="margin-top: -15px">{{ activeCaseDetail.case_description }}</div>
              <div>
                <h3>前置条件</h3>
                <n-card embedded>{{ activeCaseDetail.case_preset }}</n-card>
              </div>
              <div>
                <h3>测试步骤</h3>
                <n-data-table
                  remote
                  :columns="caseResultColumn"
                  :data="activeCaseDetail.steps || []"
                />
              </div>

              <div>
                <h3>预期结果</h3>
                <n-card embedded style="white-space: pre-line">{{
                  activeCaseDetail.case_expection
                }}</n-card>
              </div>

              <div>
                <h3>设置用例结果</h3>
                <n-select
                  v-model:value="activeCaseDetail.result"
                  :options="caseOptions"
                  style="margin-bottom: 15px"
                />
              </div>

              <div>
                <h3>备注</h3>
                <Editor
                  id="tinymce"
                  v-model="activeCaseDetail.remark"
                  tag-name="div"
                  :init="editorInit"
                />
              </div>

              <div class="rightBtn">
                <n-button
                  type="info"
                  @click="endCase"
                  v-show="!hasFinished"
                  :disabled="caseDrawerData.status"
                  >完成</n-button
                >
              </div>
            </n-card>
          </n-scrollbar>
        </n-gi>
      </n-grid>
    </n-drawer-content>
  </n-drawer>
</template>

<script>
import { defineComponent } from 'vue';
import {
  ArrowLeft32Filled as ArrowLeft,
  FullScreenMinimize24Filled as FullScreen,
  FullScreenMaximize24Filled as SmallScreen,
} from '@vicons/fluent';
import excuteDrawer from '@/views/testCenter/manual/modules/excuteDrawer.js';
import Editor from '@tinymce/tinymce-vue';
export default defineComponent({
  components: {
    ArrowLeft,
    FullScreen,
    SmallScreen,
    Editor,
  },
  setup() {
    return {
      ...excuteDrawer,
    };
  },
});
</script>
<style>
.caseDrawerContainer .n-drawer-header__main {
  width: 100%;
}
.caseDrawerContainer .n-scrollbar > .n-scrollbar-container {
  width: calc(100% - 20px);
}
.caseDrawerContainer .n-data-table .n-data-table-thead {
  display: none;
}
</style>
<style scoped lang="less">
.n-alert.n-alert--show-icon .n-alert-body {
  padding-left: 10px;
}
.caseDrawerContainer {
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    .header-left {
      display: flex;
      align-items: center;
      .backIcon {
        margin-right: 20px;
      }
    }
  }

  .caseCard {
    height: 100%;
    .alertButton {
      box-shadow: 0 4px 36px 0 rgba(190, 196, 204, 0.2);
      margin-bottom: 40px;
    }
    .alertButton:hover {
      cursor: pointer;
      box-shadow: 0 4px 20px 4px rgba(0, 0, 0, 0.4) !important;
    }
    .rightBtn {
      width: 100%;
      margin: 15px;
      display: flex;
      justify-content: center;
    }
  }
}
</style>
