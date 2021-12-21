<template>
  <n-tooltip trigger="hover">
    <template #trigger>
      <n-button
        size="medium"
        type="default"
        @click="updateModalRef.show()"
        circle
      >
        <n-icon size="26">
          <install />
        </n-icon>
      </n-button>
    </template>
    系统安装
  </n-tooltip>
  <modal-card
    title="物理机系统自动化安装"
    url="/v1/pmachine/install"
    ref="updateModalRef"
    @validate="() => updateFormRef.handlePropsButtonClick()"
    @submit="updateFormRef.post()"
  >
    <template #form>
      <system-install-form
        ref="updateFormRef"
        :machine-id="id"
        @valid="() => updateModalRef.submitCreateForm()"
        @close="
          () => {
            updateModalRef.close();
          }
        "
      />
    </template>
  </modal-card>
</template>

<script>
import { ref, defineComponent } from 'vue';
import { DiscSharp as Install } from '@vicons/ionicons5';

import ModalCard from '@/components/CRUD/ModalCard.vue';
import SystemInstallForm from './SystemInstallForm.vue';

export default defineComponent({
  components: {
    Install,
    ModalCard,
    SystemInstallForm,
  },
  props: {
    id: Number,
  },
  setup() {
    const updateModalRef = ref(null);
    const updateFormRef = ref(null);

    return {
      updateModalRef,
      updateFormRef,
    };
  },
});
</script>

<style scoped></style>
