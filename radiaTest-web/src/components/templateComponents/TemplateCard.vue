<template>
  <div style="margin-bottom: 40px">
    <n-card
      :title="createTitle(type)"
      size="huge"
      :segmented="{
        content: 'hard',
      }"
      hoverable
      header-style="
                        font-size: 20px; 
                        height: 40px;
                        padding-top: 10px;
                        padding-bottom: 10px; 
                        font-family: 'v-sans'; 
                        background-color: rgba(250,250,252,1);
                    "
      style="border-radius: 2%; overflow: hidden"
    >
      <n-grid :cols="24" :y-gap="20">
        <n-gi :span="14">
          <div style="font-size: 20px; font-weight: 400">
            总共 {{ data.length }} 个模板
          </div>
        </n-gi>
        <n-gi :span="10">
          <n-input
            v-model:value="searchName"
            placeholder="根据模板名搜索......"
            size="large"
            style="width: 95%"
            clearable
            round
          />
        </n-gi>
        <n-gi :span="24">
          <template-table :type="type" />
        </n-gi>
      </n-grid>
    </n-card>
  </div>
</template>

<script>
import { ref, inject, provide, defineComponent } from 'vue';

import TemplateTable from './TemplateTable.vue';

import { createTitle } from '@/assets/utils/createTitle.js';

export default defineComponent({
  components: {
    TemplateTable,
  },
  props: {
    type: {
      default: 'personal',
      type: String,
    },
  },
  setup(props) {
    const data = inject(props.type);
    const searchName = ref(null);
    provide('search', searchName);

    return {
      data,
      searchName,
      createTitle,
    };
  },
});
</script>

<style scoped></style>
