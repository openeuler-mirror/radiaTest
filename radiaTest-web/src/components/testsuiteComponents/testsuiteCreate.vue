<template>
  <n-form
    :label-width="40"
    :model="infoFormValue"
    :rules="infoRules"
    label-placement="top"
    ref="infoFormRef"
  >
    <n-grid :cols="18" :x-gap="24">
      <n-form-item-gi :span="10" label="测试套名" path="name">
        <n-input v-model:value="infoFormValue.name" placeholder="请设置测试套名" />
      </n-form-item-gi>

      <n-form-item-gi v-show="!data" :span="8" label="测试框架" path="framework">
        <n-select v-model:value="infoFormValue.framework_id" :options="frameworkList" />
      </n-form-item-gi>
      <n-form-item-gi :span="2" label="节点数量" path="machine_num">
        <n-input-number v-model:value="infoFormValue.machine_num" :default-value="1" :min="1" />
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
        <n-input v-model:value="infoFormValue.remark" placeholder="测试用例备注文本" />
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
            <n-button size="medium" @click="activate()" type="primary" dashed :disabled="disabled">
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
</template>

<script>
import { ref, defineComponent, computed } from 'vue';
import { Add } from '@vicons/ionicons5';
import axios from '@/axios';
import { getFramework } from '@/api/get';

export default defineComponent({
  components: {
    Add,
  },
  methods: {
    post() {
      this.infoFormRef.validate((errors) => {
        if (errors) {
          window.$message?.error('请检查输入合法性');
        } else {
          const infoCopyData = JSON.parse(JSON.stringify(this.infoFormValue));
          if (infoCopyData.add_disk) {
            infoCopyData.add_disk = infoCopyData.add_disk
              .map((item) => item.replace(' GiB', ''))
              .join(',');
          } else {
            infoCopyData.add_disk = '';
          }
          axios
            .post('/v1/suite', infoCopyData)
            .then(() => {
              window.$message?.success('创建成功!');
              this.$emit('getDataEmit');
            })
            .catch((err) => window.$message?.error(err.data.error_msg || '未知错误'));
          this.$emit('close');
        }
      });
    },
    put() {
      this.infoFormRef.validate((errors) => {
        if (errors) {
          window.$message?.error('请检查输入合法性');
        } else {
          const infoCopyData = JSON.parse(JSON.stringify(this.infoFormValue));
          if (infoCopyData.add_disk) {
            infoCopyData.add_disk = infoCopyData.add_disk
              .map((item) => item.replace(' GiB', ''))
              .join(',');
          } else {
            infoCopyData.add_disk = '';
          }
          axios
            .put(`/v1/suite/${this.data.id}`, {
              name: infoCopyData.name,
              machine_num: infoCopyData.machine_num,
              machine_type: infoCopyData.machine_type,
              add_network_interface: infoCopyData.add_network_interface,
              add_disk: infoCopyData.add_disk,
              remark: infoCopyData.remark,
            })
            .then(() => {
              window.$message?.success('修改成功!');
              this.$emit('getDataEmit');
            })
            .catch((err) => window.$message?.error(err.data.error_msg || '未知错误'));
          this.$emit('close');
        }
      });
    },
  },
  props: ['data'],
  setup(props) {
    const diskUsage = ref();
    const usageOptions = computed(() => {
      if (diskUsage.value === null) {
        return [];
      }
      return [
        {
          label: `${diskUsage.value} GiB`,
          value: `${diskUsage.value} GiB`,
        },
      ];
    });
    const frameworkList = ref();

    getFramework().then((res) => {
      frameworkList.value = res.data?.map((item) => ({ label: item.name, value: item.id }));
    });
    const infoFormRef = ref();
    const infoFormValue = ref({
      name: '',
      owner: '',
      framework_id: '',
      machine_num: '',
      machine_type: '',
      add_network_interface: '',
      add_disk: [],
      remark: '',
    });
    if (props.data) {
      const temp = JSON.parse(JSON.stringify(props.data));
      temp.add_disk ? (temp.add_disk = temp.add_disk.split(',')) : (temp.add_disk = []);
      infoFormValue.value = temp;
    }
    const infoRules = {
      name: {
        required: true,
        trigger: ['input', 'blur'],
        message: '名称必填',
      },
    };
    return {
      infoFormRef,
      infoFormValue,
      usageOptions,
      frameworkList,
      diskUsage,
      infoRules,
    };
  },
});
</script>

<style scoped></style>
