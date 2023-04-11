<template>
  <div>
    <n-form :label-width="40" :model="formValue" :rules="rules" :size="size" label-placement="top" ref="formRef">
      <n-grid :cols="18" :x-gap="24">
        <n-form-item-gi :span="6" label="产品" path="product">
          <n-select v-model:value="formValue.product" :options="productOpts" placeholder="选择产品" filterable />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="版本" path="product_id">
          <n-select v-model:value="formValue.product_id" :options="versionOpts" placeholder="选择版本" filterable />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="里程碑类型" path="type">
          <n-select
            v-model:value="formValue.type"
            :options="[
              {
                label: 'update版本',
                value: 'update'
              },
              {
                label: '迭代版本',
                value: 'round'
              },
              {
                label: '发布版本',
                value: 'release'
              }
            ]"
            placeholder="选择里程碑类型"
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
        <n-form-item-gi :span="12" path="name">
          <template #label>
            <span class="milestoneNameBox">里程碑名</span>
            <n-switch v-model:value="milestoneNameActive" @update:value="milestoneNameActiveChange">
              <template #checked> 自动生成 </template>
              <template #unchecked> 手动输入 </template>
            </n-switch>
          </template>
          <n-input
            v-model:value="formValue.name"
            :disabled="milestoneNameActive"
            placeholder="若不填写，将根据已选字段自动生成里程碑名"
            clearable
          />
        </n-form-item-gi>
        <n-form-item-gi :span="9" label="开始时间" path="start_time">
          <n-date-picker
            type="date"
            v-model:value="formValue.start_time"
            placeholder="选择版本的开始日期"
            style="width: 100%"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="9" label="结束时间" path="end_time">
          <n-date-picker
            type="date"
            v-model:value="formValue.end_time"
            placeholder="选择版本的开始日期"
            style="width: 100%"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="是否同步企业仓" v-if="hasEnterprise">
          <n-switch v-model:value="formValue.is_sync">
            <template #checked> 是 </template>
            <template #unchecked> 否 </template>
          </n-switch>
        </n-form-item-gi>
      </n-grid>
    </n-form>
  </div>
</template>

<script>
import { watch, onMounted, onUnmounted, defineComponent } from 'vue';

import validation from '@/assets/utils/validation.js';
import { createAjax } from '@/assets/CRUD/create';
import createForm from '@/views/versionManagement/milestone/modules/createForm.js';
import { getProductOpts, getVersionOpts } from '@/assets/utils/getOpts';
import { storage } from '@/assets/utils/storageUtils';
import { formatTime } from '@/assets/utils/dateFormatUtils';
import extendForm from '@/views/versionManagement/product/modules/createForm.js';

export default defineComponent({
  setup(props, context) {
    onMounted(() => {
      getProductOpts(createForm.productOpts);
      createForm.milestoneNameActive.value = true;
    });

    onUnmounted(() => {
      createForm.clean();
    });

    watch(
      () => createForm.formValue.value.product,
      () => {
        if (createForm.formValue.value.product) {
          getVersionOpts(createForm.versionOpts, createForm.formValue.value.product);
        }
      }
    );
    const hasEnterprise = storage.getValue('hasEnterprise');

    return {
      typeOptions: extendForm.typeOptions,
      handleLoad: extendForm.handleLoad,
      ...createForm,
      hasEnterprise,
      handlePropsButtonClick: () => validation(createForm.formRef, context),
      post: () => {
        createAjax.postForm('/v2/milestone', {
          value: {
            ...createForm.formValue.value,
            start_time: formatTime(createForm.formValue.value.start_time, 'yyyy-MM-dd hh:mm:ss'),
            end_time: formatTime(createForm.formValue.value.end_time, 'yyyy-MM-dd hh:mm:ss'),
            permission_type: createForm.formValue.value.permission_type.split('-')[0],
            creator_id: Number(storage.getValue('user_id')),
            org_id: storage.getValue('loginOrgId'),
            group_id: Number(createForm.formValue.value.permission_type.split('-')[1])
          }
        });
        context.emit('close');
      }
    };
  }
});
</script>

<style scoped>
.milestoneNameBox {
  margin-right: 20px;
}
</style>
