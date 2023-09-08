<template>
  <div class="synchForm">
    <n-form
      :label-width="40"
      :model="formValue"
      :rules="rules"
      :size="size"
      label-placement="top"
      ref="formRef"
    >
      <n-grid :cols="18" :x-gap="24">
        <n-form-item-gi :span="6" label="产品" path="product">
          <n-select
            v-model:value="formValue.product"
            :options="productOpts"
            placeholder="选择产品"
            filterable
          />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="版本" path="product_id">
          <n-select
            v-model:value="formValue.product_id"
            :options="versionOpts"
            placeholder="选择版本"
            filterable
          />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="类型" path="permission_type">
          <n-cascader
            v-model:value="formValue.permission_type"
            placeholder="请选择"
            :options="typeOptions"
            check-strategy="child"
            remote
            :on-load="handleLoad"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="18" label="里程碑" path="milestone_list">
          <n-select
            v-model:value="formValue.milestone_list"
            multiple
            clearable
            remote
            filterable
            placeholder="里程碑"
            :options="milestoneOpts"
            :clear-filter-after-select="false"
            :max-tag-count="2"
            @scroll="handleScroll"
            @update:value="handleUpdateValue"
            @search="handleSearch"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="18">
          <n-data-table
            :key="(row) => row.key"
            :columns="columns"
            :data="formValue.milestone_list"
            :min-height="200"
            :max-height="200"
          />
        </n-form-item-gi>
      </n-grid>
    </n-form>
  </div>
</template>

<script>
import { watch, onMounted, onUnmounted, defineComponent } from 'vue';

import validation from '@/assets/utils/validation.js';
import { createAjax } from '@/assets/CRUD/create';
import synchForm from '@/views/versionManagement/milestone/modules/synchForm.js';
import { getProductOpts, getVersionOpts, getEnterpriseOpts } from '@/assets/utils/getOpts';
import { storage } from '@/assets/utils/storageUtils';
import extendForm from '@/views/versionManagement/product/modules/createForm.js';
import { NInput, useMessage } from 'naive-ui';
import { determinMilestoneName } from '@/api/get';
export default defineComponent({
  setup(props, context) {
    onMounted(() => {
      getProductOpts(synchForm.productOpts);
      synchForm.milestoneNameActive.value = true;
      getEnterpriseOpts(synchForm.milestoneOpts, hasNext, {
        search: search.value,
        page: page.value,
        per_page: perPage,
      });
    });
    const message = useMessage();
    const hasNext = ref(true);
    const search = ref('');
    const loadingRef = ref(false);
    const hasSame = ref(false);
    let page = ref(1);
    let perPage = 30;

    const createColumns = () => [
      {
        title: '里程碑',
        key: 'title',
        render(row, index) {
          return h(NInput, {
            value: row.title,
            onUpdateValue(v) {
              synchForm.formValue.value.milestone_list[index].title = v;
              isSame(synchForm.formValue.value.milestone_list);
              determinMilestoneByName(v, index);
            },
            style: {
              background: `${row.isSame || row.isDabaSame ? 'red' : ''}`,
            },
          });
        },
      },
      {
        title: '状态',
        key: 'state',
      },
      {
        title: '用户名',
        key: 'username',
        render(row) {
          return h('div', null, { default: () => row.author.username });
        },
      },
    ];

    const handleUpdateValue = async (value) => {
      isSame(value);
      if (value.length) {
        let selectKey = value.length - 1;
        determinMilestoneByName(value[selectKey].title, selectKey);
      }
    };

    const determinMilestoneByName = (title, key) => {
      determinMilestoneName({ name: title })
        .then((res) => {
          if (res.data) {
            synchForm.formValue.value.milestone_list[key].isDabaSame = true;
          } else {
            synchForm.formValue.value.milestone_list[key].isDabaSame = false;
          }
        })
        .catch((err) => {
          window.$message?.error(err.data?.error_msg || err.message);
        });
    };

    const handleSearch = (query) => {
      search.value = query;
      synchForm.milestoneOpts.value = [];
      loadingRef.value = true;
      getEnterpriseOpts(
        synchForm.milestoneOpts,
        hasNext,
        {
          search: search.value,
          page: page.value,
          per_page: perPage,
        },
        'search'
      );
      loadingRef.value = false;
    };
    // 仓库相同name标记
    const isSame = (findArr) => {
      findArr.forEach((item, index) => {
        for (let j = index + 1; j < findArr.length; j++) {
          if (item.title === findArr[j].title) {
            item.isSame = true;
          } else {
            item.isSame = false;
          }
        }
      });
    };

    const handleScroll = async (e) => {
      const currentTarget = e.currentTarget;
      if (currentTarget.scrollTop + currentTarget.offsetHeight >= currentTarget.scrollHeight) {
        if (hasNext.value) {
          page.value = page.value + 1;
          getEnterpriseOpts(synchForm.milestoneOpts, hasNext, {
            search: search.value,
            page: page.value,
            per_page: perPage,
          });
        }
      }
    };
    onUnmounted(() => {
      synchForm.clean();
    });

    watch(
      () => synchForm.formValue.value.product,
      () => {
        if (synchForm.formValue.value.product) {
          getVersionOpts(synchForm.versionOpts, synchForm.formValue.value.product);
        }
      }
    );
    const hasEnterprise = storage.getValue('hasEnterprise');
    return {
      typeOptions: extendForm.typeOptions,
      handleLoad: extendForm.handleLoad,
      ...synchForm,
      hasEnterprise,
      handlePropsButtonClick: () => validation(synchForm.formRef, context),
      post: () => {
        hasSame.value = false;
        synchForm.formValue.value.milestone_list.forEach((item) => {
          if (item.isSame || item.isDabaSame) {
            hasSame.value = true;
            return;
          }
        });
        if (hasSame.value) {
          message.warning('里程碑重复,请重命名');
          return;
        }
        createAjax
          .postForm('/v2/milestone/batch-sync', {
            value: {
              ...synchForm.formValue.value,
              org_id: storage.getValue('loginOrgId'),
              permission_type: synchForm.formValue.value.permission_type.split('-')[0],
            },
          })
          .catch((err) => {
            window.$message?.error(err);
          });
        context.emit('close');
      },
      handleScroll,
      columns: createColumns(),
      handleUpdateValue,
      handleSearch,
    };
  },
});
</script>

<style lang="less">
.synchForm {
  width: 728px;
  .n-transfer .n-transfer-list.n-transfer-list--target {
    flex: 1.5 !important;
  }
}
</style>
