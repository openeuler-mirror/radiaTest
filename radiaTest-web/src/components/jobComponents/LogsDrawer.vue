<template>
  <n-drawer v-model:show="active" :width="1800" :placement="right">
    <n-drawer-content
      header-style="justify-content: center;"
      body-style="background-color: rgba(240,241,244,1)"
    >
      <template #header>
        <p style="width: 1700px; text-align: center; margin: 0">
          <n-button
            @click="
              () => {
                active = false;
              }
            "
            size="medium"
            style="float: left;"
            quaternary
            circle
          >
            <n-icon :size="26">
              <arrow-left />
            </n-icon>
          </n-button>
          <span style="line-height: 34px; font-size: 28px">
            {{ title }}
          </span>
        </p>
      </template>
      <n-grid :cols="36" :x-gap="12" style="height: 100%">
        <n-gi :span="8">
          <n-card class="caseCard" hoverable>
            <div style="width: 100%; margin-bottom: 20px;">
              <n-space item-style="display: flex;" align="center" justify="end">
                <n-checkbox v-model:checked="successCheck">成功用例</n-checkbox>
                <n-checkbox v-model:checked="failCheck">失败用例</n-checkbox>
              </n-space>
            </div>
            <div style="width: 100%; margin-bottom: 20px;">
              <n-input
                v-model:value="searchCaseValue"
                placeholder="搜索用例"
                size="large"
                clearable
                round
              />
            </div>
            <div v-for="_analyzed in analyzeds" :key="_analyzed.id">
              <n-alert
                class="alertButton"
                :title="_analyzed.case"
                :id="_analyzed.case"
                :type="_analyzed.result === 'success' ? 'success' : 'error'"
                @click="handleSelectCase(_analyzed.case)"
              >
                用时:
              </n-alert>
            </div>
          </n-card>
        </n-gi>
        <n-gi :span="8">
          <n-card class="analyzedCard" hoverable>
            <n-timeline>
              <n-timeline-item
                v-for="record in records"
                :key="record.id"
                :id="record.id"
                :type="createTimelineType(record.result)"
                :title="record.job"
                :content="
                  !record.fail_type && record.result === 'success'
                    ? '测试通过'
                    : record.fail_type
                "
                :time="record.create_time"
                @click="() => handleSelectRecord(record)"
              />
            </n-timeline>
          </n-card>
        </n-gi>
        <n-gi :span="20">
          <div v-if="selectedRecord" class="logCard" style="overflow-y: scroll">
            <n-card hoverable>
              <n-list>
                <n-list-item>
                  <n-thing>
                    <template #header>用例描述 </template>
                    <pre>{{ caseDetail.description }}</pre>
                  </n-thing>
                </n-list-item>
                <n-list-item>
                  <n-thing>
                    <template #header>问题描述</template>
                    <template #header-extra>
                      <n-button text @click="() => updateModalRef.show()">
                        <template #icon>
                          <edit />
                        </template>
                      </n-button>
                      <modal-card
                        :initY="100"
                        :initX="300"
                        title="编辑问题信息"
                        ref="updateModalRef"
                        @validate="() => updateFormRef.handlePropsButtonClick()"
                        @submit="updateFormRef.put()"
                      >
                        <template #form>
                          <failure-update-form
                            ref="updateFormRef"
                            :data="selectedRecord"
                            @valid="() => updateModalRef.submitCreateForm()"
                            @close="
                              () => {
                                updateModalRef.close();
                                emitUpdateEvent();
                              }
                            "
                          />
                        </template>
                      </modal-card>
                    </template>
                    <pre>{{ selectedRecord.details }}</pre>
                  </n-thing>
                </n-list-item>
              </n-list>
              <div>
                <n-space justify="center" :size="100" style="margin-top: 40px">
                  <n-button
                    size="large"
                    type="primary"
                    @click="handleLogUrlRedirect(selectedRecord.log_url)"
                  >
                    查看完整日志
                  </n-button>
                  <n-button
                    size="large"
                    type="error"
                    @click="handleNewIssueRedirect(caseDetail.suite)"
                    >创建issue</n-button
                  >
                </n-space>
              </div>
            </n-card>
            <n-card size="huge" segment="false" hoverable>
              <template #header>
                <p>
                  <n-icon
                    v-if="selectedRecord.result === 'fail'"
                    :size="20"
                    color="rgba(206,64,64,1)"
                  >
                    <cancel-filled />
                  </n-icon>
                  <n-icon v-else :size="20" color="green">
                    <check-circle />
                  </n-icon>
                  <span style="padding-left: 20px">{{
                    selectedRecord.result === 'success'
                      ? '执行成功'
                      : '执行失败'
                  }}</span>
                </p>
                <p
                  style="font-size: 12px; font-weight: 400; padding-left: 40px"
                >
                  用时:
                </p>
              </template>
              <template #header-extra>
                <p style="font-size: 18px; font-weight: 600">
                  {{ selectedStage }}
                </p>
              </template>
              <log-data-table :data="logsData" />
            </n-card>
          </div>
        </n-gi>
      </n-grid>
    </n-drawer-content>
  </n-drawer>
</template>

<script>
import { defineComponent } from 'vue';

import ModalCard from '@/components/CRUD/ModalCard.vue';
import { CancelFilled } from '@vicons/material';
import { CheckCircle, Edit } from '@vicons/fa';
import LogDataTable from './LogDataTable';
import { ArrowLeft32Filled as ArrowLeft } from '@vicons/fluent';
import FailureUpdateForm from './FailureUpdateForm.vue';

import logsDrawer from '@/views/job/modules/logsDrawer.js';

export default defineComponent({
  components: {
    LogDataTable,
    CancelFilled,
    CheckCircle,
    ArrowLeft,
    Edit,
    ModalCard,
    FailureUpdateForm,
  },
  setup() {
    return {
      ...logsDrawer,
    };
  },
});
</script>

<style scoped>
.caseCard {
  height: 100%;
}
.analyzedCard {
  height: 100%;
}
.logCard {
  height: 100%;
}
.logArea {
  height: 80%;
  border-style: none;
  box-shadow: 0 0 10px #f5f6f8;
  background-color: white;
}
.alertButton {
  box-shadow: 0 4px 36px 0 rgba(190, 196, 204, 0.2);
  margin-bottom: 40px;
}
.alertButton:hover {
  cursor: pointer;
  box-shadow: 0 4px 20px 4px rgba(0, 0, 0, 0.4) !important;
}
</style>
