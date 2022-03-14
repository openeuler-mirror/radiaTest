<template>
  <div>
    <n-card hoverable>
      <collapse-list :list="list" />
      <div>
        <n-space justify="center" style="padding-top: 5px">
          <n-button @click="() => updateModalRef.show()"> 编辑问题 </n-button>
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
                @close="closeForm"
              />
            </template>
          </modal-card>
          <n-button type="error" @click="createIssue"> 创建issue </n-button>
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
            selectedRecord.result === 'success' ? '执行成功' : '执行失败'
          }}</span>
        </p>
        <p style="font-size: 12px; font-weight: 400; padding-left: 40px">
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
</template>
<script>
import { ref } from 'vue';
import { CancelFilled } from '@vicons/material';
import { CheckCircle } from '@vicons/fa';
import LogDataTable from '@/components/jobComponents/LogDataTable';
import CollapseList from '@/components/collapseList/collapseList.vue';
import FailureUpdateForm from '@/components/jobComponents/FailureUpdateForm.vue';
import ModalCard from '@/components/CRUD/ModalCard.vue';
export default {
  components: {
    CancelFilled,
    CheckCircle,
    LogDataTable,
    ModalCard,
    FailureUpdateForm,
    CollapseList,
  },
  props: ['list', 'logsData', 'selectedStage', 'selectedRecord'],
  setup() {
    const updateModalRef = ref(null);
    const updateFormRef = ref(null);
    return {
      updateModalRef,
      updateFormRef,
    };
  },
  methods: {
    createIssue() {
      this.$emit('createIssue');
    },
    closeForm() {
      this.$refs.updateModalRef.close();
      this.$emit('updateEvent');
    },
  },
};
</script>
