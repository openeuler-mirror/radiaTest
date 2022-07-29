<template>
  <n-card
    title="产品版本"
    size="huge"
    :segmented="{
      content: 'hard'
    }"
    header-style="
            font-size: 30px;
            height: 80px;
            font-family: 'v-sans';
            padding-top: 40px;
            background-color: rgb(242,242,242);
        "
    style="height: 100%"
  >
    <!-- <selection-button
      @show="tableRef.showSelection()"
      @off="tableRef.offSelection()"
    /> -->
    <n-grid x-gap="24" y-gap="6">
      <n-gi :span="6">
        <n-space>
          <create-button title="注册产品版本" @click="createModalRef.show()" />
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
          <!-- <delete-button title="产品版本" url="/v1/product" /> -->
        </n-space>
      </n-gi>
      <n-gi :span="16"> </n-gi>
      <n-gi :span="2">
        <div class="titleBtnWrap">
          <filterButton class="item" :filterRule="filterRule" @filterchange="filterchange"></filterButton>
          <refresh-button @refresh="tableRef.refreshData()">
            刷新版本列表
          </refresh-button>
        </div>
      </n-gi>
      <n-gi :span="24"></n-gi>
      <n-gi :span="24"></n-gi>
      <n-gi :span="24"> </n-gi>
      <n-gi :span="24">
        <product-table ref="tableRef" @update="() => updateModalRef.show()" />
        <modal-card
          title="修改产品版本"
          url="/v1/product"
          ref="updateModalRef"
          @validate="() => updateFormRef.handlePropsButtonClick()"
          @submit="updateFormRef.put()"
        >
          <template #form>
            <product-update-form
              ref="updateFormRef"
              @valid="() => updateModalRef.submitCreateForm()"
              @close="
                () => {
                  updateModalRef.close();
                }
              "
            />
          </template>
        </modal-card>
        <extend-drawer />
      </n-gi>
    </n-grid>
    <template #action>
      <n-divider />
      <div
        style="
          text-align: center;
          color: grey;
          padding-top: 15px;
          padding-bottom: 0;
        "
      >
        {{ settings.name }} {{ settings.version }} · {{ settings.license }}
      </div>
    </template>
  </n-card>
</template>

<script>
import { ref, defineComponent } from 'vue';

import settings from '@/assets/config/settings.js';
import Common from '@/components/CRUD';
import Essential from '@/components/productComponents';
import filterButton from '@/components/filter/filterButton.vue';
import { useStore } from 'vuex';

export default defineComponent({
  components: {
    ...Common,
    ...Essential,
    filterButton
  },
  // eslint-disable-next-line max-lines-per-function
  setup() {
    const tableRef = ref(null);
    const createFormRef = ref(null);
    const updateFormRef = ref(null);
    const createModalRef = ref(null);
    const updateModalRef = ref(null);
    const store = useStore();
    const storeObj = ref({
      name: '',
      version: '',
      description: ''
    });
    const filterRule = ref([
      {
        path: 'name',
        name: '产品名称',
        type: 'input'
      },
      {
        path: 'version',
        name: '版本名称',
        type: 'input'
      },
      {
        path: 'description',
        name: '描述信息',
        type: 'input'
      }
    ]);

    const filterchange = (filterArray) => {
      storeObj.value = { name: '', version: '', description: '' };
      filterArray.forEach((v) => {
        storeObj.value[v.path] = v.value;
      });

      store.commit('filterProduct/setName', storeObj.value.name);
      store.commit('filterProduct/setVersion', storeObj.value.version);
      store.commit('filterProduct/setDescription', storeObj.value.description);
    };

    return {
      settings,
      tableRef,
      createFormRef,
      updateFormRef,
      createModalRef,
      updateModalRef,
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

  .item {
    margin: 0 20px;
  }
}
</style>
