<template>
  <div class="title">服务器性能监控</div>
  <div id="cpu-pie" class="chart-box square-box"></div>
  <div id="mem-pie" class="chart-box square-box"></div>
  <div id="disk-pie" class="chart-box square-box"></div>
  <div id="performance-line" class="chart-box rect-box"></div>
  <div class="title" style="display: inline-block; width: calc(100% - 670px)">
    网络性能监控
  </div>
  <div class="title" style="display: inline-block">其他信息</div>
  <div class="chart-box rect-box">
    <p class="chart-text">
      <n-icon :size="20" color="#a2d48c" style="top: 5px">
        <arrow-up />
      </n-icon>
      <span class="subtext">上行速度:</span>
      <span class="cur-data">{{ uploadSpeed }}</span>
      <span class="subtext" style="color: black; margin-right: 40px"
        >Bytes / s</span
      >
      <n-icon :size="20" color="#5470c6" style="top: 5px">
        <arrow-down />
      </n-icon>
      <span class="subtext">下行速度:</span>
      <span class="cur-data">{{ downloadSpeed }}</span>
      <span class="subtext" style="color: black; margin-right: 40px"
        >Bytes / s</span
      >
    </p>
    <div id="network-line" style="height: 200px; width: calc(100%)"></div>
  </div>
  <div id="swap-pie" class="chart-box square-box"></div>
  <div class="chart-box" style="width: 420px">
    <div style="display: flex; flex-wrap: wrap; width: 100%">
      <div class="stat-info">
        <p>
          <span class="number">{{ vmNum }}</span>
          <span>台</span>
        </p>
        <p class="subtitle">当前机器正在运行的虚拟机数量</p>
      </div>
      <div class="stat-info">
        <p>
          <span class="number">{{ physicalCpuCores }}</span>
          <span class="subtitle">物理核心</span>
          <span> / </span>
          <span class="number">{{ logicalCpuCores }}</span>
          <span class="subtitle">逻辑核心 </span>
        </p>
        <p class="subtitle">当前机器的超线程状态</p>
      </div>
      <div class="stat-info">
        <p>
          <span class="number">{{ memoryTotal }}</span>
          <span>GiB</span>
        </p>
        <p class="subtitle">当前机器当内存总量</p>
      </div>
      <div class="stat-info">
        <p>
          <span class="number">{{ diskTotal }}</span>
          <span>GiB</span>
        </p>
        <p class="subtitle">当前机器当磁盘总量</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';
import { ArrowUp, ArrowDown } from '@vicons/ionicons5';
import { Socket } from '@/socket';
import { init } from 'echarts';
import { settings } from '@/assets/config/settings.js';
import resourceCharts from '@/views/pmachine/modules/expandedContent/resourceChart.js';

export default defineComponent({
  name: 'resourceCharts',
  components: {
    ArrowUp,
    ArrowDown,
  },
  props: {
    ip: String,
    listen: String,
    machineGroupIp:String,
    data:Object
  },
  setup(props) {
    let charts = null;
    const data = {
      performanceData: ref([]),
      networkData: ref([]),
      downloadSpeed: ref(0),
      uploadSpeed: ref(0),
      vmNum: ref(0),
      physicalCpuCores: ref(0),
      logicalCpuCores: ref(0),
      memoryTotal: ref(0),
      diskTotal: ref(0),
    };
    const resourceMonitorSocket = new Socket(
      `${settings.websocketProtocol}://${props.machineGroupIp}:${props.data.machine_group.messenger_listen}/monitor/host`
    );
    resourceMonitorSocket.connect();

    onMounted(() => {
      charts = {
        performanceLine: init(document.getElementById('performance-line')),
        networkLine: init(document.getElementById('network-line')),
        cpuPie: init(document.getElementById('cpu-pie')),
        memPie: init(document.getElementById('mem-pie')),
        diskPie: init(document.getElementById('disk-pie')),
        swapPie: init(document.getElementById('swap-pie')),
      };
      resourceCharts.createEcharts(charts);
      resourceMonitorSocket.emit('start', {
        ip: props.ip,
        listen: props.listen,
      });
      resourceMonitorSocket.listen(props.machineGroupIp, (res) =>
        resourceCharts.listenResponse(res, charts, data)
      );
    });

    onUnmounted(() => {
      resourceCharts.disposeEcharts(charts);
      resourceMonitorSocket.disconnect();
      charts = null;
    });

    return {
      ...data,
      ...resourceCharts,
    };
  },
});
</script>

<style scoped>
.title {
  padding-left: 10px;
  padding-top: 10px;
  font-size: 18px;
  font-weight: 600;
}
.chart-box {
  height: 200px;
  display: inline-block;
  vertical-align: middle;
  margin: 10px;
  background-color: white;
}
.rect-box {
  width: calc(100% - 680px);
}
.square-box {
  width: 200px;
}
.chart-text {
  float: right;
}
.subtext {
  font-size: 12px;
  color: grey;
  margin-right: 10px;
}
.cur-data {
  font-size: 14px;
  color: #1e93ff;
  margin-right: 10px;
}
.stat-info {
  width: 50%;
}
.stat-info p {
  text-align: center;
}
.stat-info .number {
  font-size: 20px;
  margin-right: 5px;
  color: #40a3ff;
}
.stat-info .subtitle {
  color: grey;
  font-size: 10px;
}
</style>
