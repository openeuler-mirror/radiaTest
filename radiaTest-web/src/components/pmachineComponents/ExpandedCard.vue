<template>
  <n-card hoverable>
    <n-space vertical>
      <n-tabs type="line" justify-content="space-evenly">
        <n-tab-pane name="configs" tab="配置概览">
          <n-grid x-gap="24" y-gap="48">
            <n-gi :span="24"></n-gi>
            <n-gi :span="6">
              <n-space vertical>
                <n-p>ssh用户名：{{ SSHUSER }}</n-p>
                <n-p>ssh端口：{{ SSHPORT }}</n-p>
                <n-p>ssh密码：{{ SSHPASSWORD }}</n-p>
                <n-p v-show="DESCRIPTION === 'as the host of ci'">
                  CI端口：{{ LISTEN }}
                </n-p>
              </n-space>
            </n-gi>
            <n-gi :span="10">
              <n-space vertical>
                <n-p>内存容量：{{ memoryTotal }} GiB</n-p>
                <n-p>CPU核心：{{ cpuPhysicalCores }}</n-p>
                <n-p>CPU型号：{{ cpuIndex }}</n-p>
              </n-space>
            </n-gi>
            <n-gi :span="4">
              <n-space vertical>
                <n-progress
                  type="circle"
                  :stroke-width="10"
                  :percentage="memoryPercentage"
                >
                  <n-space vertical>
                    <n-p class="memoryUse">{{ memoryUse }}</n-p>
                    <n-p style="text-align: center">GiB</n-p>
                  </n-space>
                </n-progress>
                <n-p class="usageText">内存用量</n-p>
              </n-space>
            </n-gi>
            <n-gi :span="4">
              <n-space vertical>
                <n-progress
                  type="circle"
                  :stroke-width="10"
                  :percentage="cpuPercentage"
                />
                <n-p class="usageText">CPU用量</n-p>
              </n-space>
            </n-gi>
            <n-gi :span="24"></n-gi>
          </n-grid>
        </n-tab-pane>
        <n-tab-pane
          :disabled="DESCRIPTION !== 'as the host of ci'"
          name="monitor"
          tab="资源监控"
        >
          <div style="height: 540px; background-color: #f2f3f6">
            <resource-charts ref="charts" :ip="IP" :listen="LISTEN" />
          </div>
        </n-tab-pane>
      </n-tabs>
    </n-space>
  </n-card>
</template>

<script>
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';
import { Socket } from '@/socket';

import settings from '@/assets/config/settings.js';
import ResourceCharts from './expandedContent/ResourceCharts';

export default defineComponent({
  components: {
    ResourceCharts,
  },
  props: {
    SSHUSER: String,
    SSHPASSWORD: String,
    SSHPORT: String,
    LISTEN: Number,
    DESCRIPTION: String,
    IP: String,
  },
  setup(props) {
    const memoryTotal = ref('');
    const cpuPhysicalCores = ref('');
    const cpuIndex = ref('');
    const memoryPercentage = ref('');
    const memoryUse = ref('');
    const cpuPercentage = ref('');

    const resourceMonitorSocket = new Socket(
      `ws://${settings.serverPath}/monitor/normal`
    );

    onMounted(() => {
      resourceMonitorSocket.connect();

      resourceMonitorSocket.emit('start', {
        ip: props.IP,
        user: props.SSHUSER,
        port: props.SSHPORT,
        password: props.SSHPASSWORD,
      });

      resourceMonitorSocket.listen(props.IP, (res) => {
        cpuPercentage.value = res.cpu_usage.toFixed(2);
        memoryTotal.value = res.mem_total.toFixed(2);
        memoryPercentage.value = res.mem_usage.toFixed(2);
        memoryUse.value = (
          (memoryPercentage.value * memoryTotal.value) /
          100
        ).toFixed(2);
        cpuPhysicalCores.value = res.cpu_physical_cores;
        cpuIndex.value = res.cpu_index;
      });
    });

    onUnmounted(() => {
      resourceMonitorSocket.emit('end', props.IP);
      resourceMonitorSocket.disconnect();
    });

    return {
      memoryTotal,
      cpuPhysicalCores,
      cpuIndex,
      memoryPercentage,
      memoryUse,
      cpuPercentage,
    };
  },
});
</script>

<style scoped>
.memoryUse {
  font-size: 17px;
}
.usageText {
  position: relative;
  left: 32px;
}
</style>
