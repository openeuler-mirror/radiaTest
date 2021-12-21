<template>
  <n-drawer v-model:show="active" :width="1000" placement="right">
    <n-drawer-content>
      <template #header>
        <p style="width: 900px; text-align: center; margin: 0">
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
          {{ rowData.name }}-{{ rowData.version }}
        </p>
      </template>
      <div style="margin-top: 20px; margin-bottom: 20px">
        <product-milestone-card :form="rowData" />
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script>
import { defineComponent } from 'vue';

import ProductMilestoneCard from './ProductMilestoneCard.vue';
import { ArrowLeft32Filled as ArrowLeft } from '@vicons/fluent';

import productTable from '@/views/product/modules/productTable.js';

export default defineComponent({
  components: {
    ProductMilestoneCard,
    ArrowLeft,
  },
  setup() {
    return {
      active: productTable.active,
      rowData: productTable.rowData,
    };
  },
});
</script>
