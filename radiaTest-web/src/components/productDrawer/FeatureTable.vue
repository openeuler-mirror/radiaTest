<template>
  <n-data-table
    :loading="featureLoading"
    :columns="featureListColumns"
    :data="featureListData"
    :bordered="false"
  />
</template>

<script>
import { onMounted, onUnmounted, defineComponent } from 'vue';
import { 
  featureLoading, 
  featureListColumns, 
  featureListData,
  getFeatureList,
  cleanData 
} from '@/views/versionManagement/product/modules/productDetailDrawer.js';

export default defineComponent({
  props: {
    qualityboardId: Number,
    type: {
      type: String,
      default: 'addition',
    }
  },
  setup(props) {
    onMounted(() => {
      getFeatureList(props.qualityboardId, props.type);
    });
    onUnmounted(() => {
      cleanData();
    });
    
    return {
      featureListColumns,
      featureListData,
      featureLoading,
    };
  }
});
</script>

<style scoped>
  :deep(.feature-no){
    width: 80px;
  }
  :deep(.feature-name){
    width: 200px;
  }
  :deep(.feature-sig){
    width: 200px;
  }
  :deep(.feature-owner){
    width: 200px;
  }
  :deep(.feature-release-to){
    width: 80px;
  }
  :deep(.feature-task-status){
    width: 120px;
  }
</style>
