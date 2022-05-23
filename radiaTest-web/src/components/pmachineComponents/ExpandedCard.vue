<template>
  <n-card hoverable>
    <n-space vertical>
      <n-tabs
        type="line"
        justify-content="space-evenly"
        @update:value="switchTab"
      >
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
            <resource-charts
              ref="charts"
              :data="data"
              :ip="IP"
              :listen="LISTEN"
              :machineGroupIp="machine_group_ip"
            />
          </div>
        </n-tab-pane>
        <n-tab-pane
          name="console"
          tab="控制台"
          display-directive="show"
          :disabled="true"
        >
          <div style="overflow: auto">
            <div
              :id="'console' + IP.replaceAll('.', '')"
              :style="{
                height: termHeight + 'px',
                width: termWidth + 'px',
              }"
            ></div>
            <div
              style="
                display: flex;
                justify-content: center;
                align-items: center;
                overflow: hidden;
              "
            >
              <n-slider
                v-model:value="termWidth"
                @update:value="resizeTerm"
                :max="1400"
                :min="800"
              />
            </div>
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
import { createTerminal } from '@/assets/utils/xterm.js';
import { FitAddon } from 'xterm-addon-fit';

export default defineComponent({
  components: {
    ResourceCharts,
  },
  props: {
    data: Object,
    SSHUSER: String,
    SSHPASSWORD: String,
    SSHPORT: String,
    LISTEN: Number,
    DESCRIPTION: String,
    IP: String,
    messenger_listen: String || Number,
    machine_group_ip: String
  },
  data() {
    return {
      term: null,
      fitAddon: null,
      termSocket: new Socket(`${settings.websocketProtocol}://${settings.serverPath}/xterm?machine_group_ip=${this.machine_group_ip}&messenger_listen=${this.messenger_listen}&machine_ip=${this.IP}`),
    };
  },
  methods: {
    switchTab(value) {
      if (value === 'console' && !this.termSocket?.isConnect()) {
        this.connectXterm();
      }
    },
    resizeTerm() {
      this.termSocket.emit('resize', {
        cols: this.termHeight,
        rows: this.termWidth,
        machine_ip: this.IP,
        machine_group_ip: this.machine_group_ip,
        messenger_listen: this.messenger_listen
      });
      this.fitAddon.fit();
    },
    startConsole() {
      this.termSocket.emit('start', {
        machine_ip: this.IP,
        port: this.SSHPORT,
        user: this.SSHUSER,
        password: this.SSHPASSWORD,
        cols: this.termHeight,
        rows: this.termWidth,
        machine_group_ip: this.machine_group_ip,
        messenger_listen: this.messenger_listen
      });
      this.termSocket.listen(`${this.IP}=>${this.machine_group_ip}=>xterm`, data => {
        this.term.write(data.mesg);
      });
    },
    connectXtermDom() {
      this.term = createTerminal();
      this.term.open(document.getElementById(`console${this.IP.replaceAll('.', '')}`));
      this.fitAddon = new FitAddon();
      this.term.loadAddon(this.fitAddon);
      this.fitAddon.fit();
      this.term.focus();
      this.startConsole();
      this.listenXterm();
      this.resizeTerm();
    },
    connectXterm() {
      this.termSocket.connect();
      if (this.termSocket.isConnect()) {
        this.connectXtermDom();
      } else {
        this.termSocket.connect();
        this.connectXtermDom();
      }
    },
    listenXterm() {
      this.term.onData(data => {
        this.termSocket.emit('command', {
          command: data, machine_ip: this.IP, machine_group_ip: this.machine_group_ip,
          messenger_listen: this.messenger_listen
        });
      });
    }
  },
  setup(props) {
    const memoryTotal = ref('');
    const cpuPhysicalCores = ref('');
    const cpuIndex = ref('');
    const memoryPercentage = ref('');
    const memoryUse = ref('');
    const cpuPercentage = ref('');
    const resourceMonitorSocket = new Socket(
      `ws://${props.machine_group_ip}:${props.messenger_listen}/monitor/normal`
    );
    onMounted(() => {
      resourceMonitorSocket.connect();
      resourceMonitorSocket.emit('start', {
        ip: props.IP,
        user: props.SSHUSER,
        port: props.data.port,
        password: props.SSHPASSWORD,
        messenger_listen: props.messenger_listen,
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
      resourceMonitorSocket.emit('end', { ip: props.IP });
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
