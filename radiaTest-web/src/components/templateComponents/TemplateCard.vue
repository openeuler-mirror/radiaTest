<template>
  <div style="margin-bottom: 40px">
    <n-card
      :title="createTitle(type)"
      size="huge"
      :segmented="{
        content: 'hard'
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
        <n-gi :span="23">
          <div style="font-size: 20px; font-weight: 400">总共 {{ data.length }} 个模板</div>
        </n-gi>
        <n-gi :span="1" class="titleBtnWrap">
          <filterButton class="item" :filterRule="filterRule" @filterchange="filterchange"></filterButton>
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
import filterButton from '@/components/filter/filterButton.vue';

export default defineComponent({
  components: {
    TemplateTable,
    filterButton
  },
  props: {
    type: {
      default: 'personal',
      type: String
    }
  },
  setup(props) {
    const data = inject(props.type);
    const searchName = ref(null);
    provide('search', searchName);
    const filterRule = ref([
      {
        path: 'searchName',
        name: '模板名',
        type: 'input'
      }
    ]);

    const filterchange = (filterArray) => {
      searchName.value = filterArray[0]?.value || null;
    };

    return {
      data,
      searchName,
      createTitle,
      filterRule,
      filterchange
    };
  }
});
</script>

<style scoped lang="less">
.titleBtnWrap {
  display: flex;
  align-items: center;
}
</style>
