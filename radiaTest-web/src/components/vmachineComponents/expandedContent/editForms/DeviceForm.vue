<template>
  <n-space item-style="display: flex;" vertial>
    <n-checkbox-group v-model:value="selectedDevice">
      <div v-for="(item, i) in deviceList" :key="i">
        <n-checkbox :value="item" :label="item.service" />
        <n-code :code="item.device" language="xml" />
      </div>
    </n-checkbox-group>
  </n-space>
</template>

<script>
import {
  ref,
  watch,
  onMounted,
  defineComponent,
  getCurrentInstance,
} from 'vue';

import { specialDevice } from '@/assets/config/vmachineSpecialDevice.js';

export default defineComponent({
  props: {
    data: Object,
  },
  // eslint-disable-next-line max-lines-per-function
  setup(props) {
    const { proxy } = getCurrentInstance();
    const deviceList = ref([]);
    const selectedDevice = ref([]);
    const getData = () => {
      try {
        deviceList.value = specialDevice.filter(
          (item) => !props.data.special_device.split(',').includes(item.service)
        );
      } catch {
        deviceList.value = specialDevice;
      }
    };
    onMounted(() => {
      getData();
    });
    watch(
      props,
      () => {
        getData();
      },
      { deep: true }
    );
    return {
      deviceList,
      selectedDevice,
      submit(ctx) {
        proxy.$axios
          .post('/v1/vmachine/attach', {
            vmachine_id: props.data.id,
            device: selectedDevice.value,
          })
          .then((resps) => {
            if (resps.length) {
              resps.forEach((resp) => {
                if (resp.error_code !== 0) {
                  window.$message?.error(resp.error_mesg);
                } else {
                  window.$message?.success(`${resp.service}配置添加成功`);
                }
              });
            }
          })
          .catch(() => {
            window.$message?.error('发生未知错误，请联系管理员处理');
          })
          .finally(() => {
            ctx.emit('refresh');
          });
      },
    };
  },
});
</script>
