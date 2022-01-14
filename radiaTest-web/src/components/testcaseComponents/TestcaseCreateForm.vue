<template>
  <div v-show="tab === 'info'">
    <n-form
      :label-width="40"
      :model="infoFormValue"
      :rules="infoRules"
      :size="size"
      label-placement="top"
      ref="infoFormRef"
    >
      <n-grid :cols="18" :x-gap="24">
        <n-form-item-gi :span="8" label="测试套" path="suite">
          <n-select
            v-model:value="infoFormValue.suite"
            placeholder="请选择所属测试套"
            :options="suiteOptions"
            filterable
          />
        </n-form-item-gi>
        <n-form-item-gi :span="10" label="测试用例名" path="name">
          <n-input
            v-model:value="infoFormValue.name"
            placeholder="请设置测试用例名"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="4" label="测试级别" path="test_level">
          <n-select
            v-model:value="infoFormValue.test_level"
            :options="[
              {
                label: '系统测试',
                value: '系统测试',
              },
              {
                label: '集成测试',
                value: '集成测试',
              },
              {
                label: '单元测试',
                value: '单元测试',
              },
            ]"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="4" label="测试类型" path="test_type">
          <n-select
            v-model:value="infoFormValue.test_type"
            :options="[
              {
                label: '功能测试',
                value: '功能测试',
              },
              {
                label: '安全测试',
                value: '安全测试',
              },
              {
                label: '性能测试',
                value: '性能测试',
              },
              {
                label: '压力测试',
                value: '压力测试',
              },
              {
                label: '可靠性测试',
                value: '可靠性测试',
              },
            ]"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="责任人" path="owner">
          <n-input
            v-model:value="infoFormValue.owner"
            placeholder="请输入已在平台注册用户的用户名"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="4" label="是否自动化" path="automatic">
          <n-select
            v-model:value="infoFormValue.automatic"
            :options="[
              {
                label: '是',
                value: true,
              },
              {
                label: '否',
                value: false,
              },
            ]"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="2" label="节点数量" path="machine_num">
          <n-input-number
            v-model:value="infoFormValue.machine_num"
            :default-value="1"
            :min="1"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="4" label="节点类型" path="machine_type">
          <n-select
            v-model:value="infoFormValue.machine_type"
            :options="[
              {
                label: '虚拟机',
                value: 'kvm',
              },
              {
                label: '物理机',
                value: 'physical',
              },
            ]"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="12" label="备注" path="remark">
          <n-input
            v-model:value="infoFormValue.remark"
            placeholder="测试用例备注文本"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="2" label="增加网卡" path="add_network_interface">
          <n-input-number
            v-model:value="infoFormValue.add_network_interface"
            :default-value="0"
            :min="0"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="16" label="增加磁盘" path="add_disk">
          <n-dynamic-tags v-model:value="infoFormValue.add_disk" size="large">
            <template #input="{ submit }">
              <n-auto-complete
                size="medium"
                :options="usageOptions"
                v-model:value="diskUsage"
                placeholder="磁盘容量"
                :clear-after-select="true"
                @select="submit($event)"
              />
            </template>
            <template #trigger="{ activate, disabled }">
              <n-button
                size="medium"
                @click="activate()"
                type="primary"
                dashed
                :disabled="disabled"
              >
                <template #icon>
                  <n-icon>
                    <Add />
                  </n-icon>
                </template>
                添加磁盘
              </n-button>
            </template>
          </n-dynamic-tags>
        </n-form-item-gi>
      </n-grid>
    </n-form>
  </div>
  <div v-show="tab === 'content'">
    <n-form
      :label-width="40"
      :model="contentFormValue"
      :rules="contentRules"
      :size="size"
      label-placement="top"
      ref="contentFormRef"
    >
      <n-grid :cols="18" :x-gap="24">
        <n-form-item-gi :span="18" label="用例描述" path="description">
          <n-input
            v-model:value="contentFormValue.description"
            type="textarea"
            :autosize="{
              minRows: 2,
            }"
            placeholder="请准确描述此用例"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="18" label="预置条件" path="preset">
          <n-input
            v-model:value="contentFormValue.preset"
            type="textarea"
            :autosize="{
              minRows: 2,
            }"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="18" label="操作步骤" path="steps">
          <n-input
            v-model:value="contentFormValue.steps"
            type="textarea"
            :autosize="{
              minRows: 4,
            }"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="18" label="预期结果" path="expection">
          <n-input
            v-model:value="contentFormValue.expection"
            type="textarea"
            :autosize="{
              minRows: 3,
            }"
          />
        </n-form-item-gi>
      </n-grid>
    </n-form>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';

import { Add } from '@vicons/ionicons5';

import { createAjax } from '@/assets/CRUD/create';
import createForm from '@/views/caseManage/testcase/modules/createForm.js';

export default defineComponent({
  components: {
    Add,
  },
  setup(props, context) {
    onMounted(() => {
      createForm.initSuiteOptions();
    });
    onUnmounted(() => {
      createForm.clean();
    });

    return {
      ...createForm,
      handlePropsButtonClick: () => createForm.validateFormData(context),
      changeTabs: (tabValue) => {
        createForm.tab.value = tabValue;
      },
      post: () => {
        return new Promise((resolve, reject) => {
          const infoCopyData = JSON.parse(
            JSON.stringify(createForm.infoFormValue.value)
          );
          if (infoCopyData.add_disk) {
            infoCopyData.add_disk = infoCopyData.add_disk
              .map((item) => item.replace(' GiB', ''))
              .join(',');
          } else {
            infoCopyData.add_disk = '';
          }
          const postData = ref(
            Object.assign(infoCopyData, createForm.contentFormValue.value)
          );
          createAjax.postForm('/v1/case', postData).then(res=>resolve(res)).catch(err=>reject(err));
          context.emit('close');
        });
      },
    };
  },
});
</script>

<style scoped></style>
