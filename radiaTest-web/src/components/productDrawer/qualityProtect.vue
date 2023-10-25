<template>
  <div>
    <n-card>
      <n-grid x-gap="12" :cols="4">
        <n-gi
          id="daily-build"
          :span="1"
          class="item"
          @click="handleClick('daily-build')"
          @mouseenter="handleMouseEnter('daily-build')"
          @mouseleave="handleMouseLeave('daily-build')"
          style="cursor: pointer"
        >
          <n-progress
            :color="renderColor(dailyBuildPassed)"
            type="dashboard"
            gap-position="bottom"
            :percentage="dailyBuildCompletion"
          />
          <p>每日构建</p>
        </n-gi>
        <n-gi
          id="rpm-check"
          :span="1"
          class="item"
          @click="handleClick('rpm-check')"
          @mouseenter="handleMouseEnter('rpm-check')"
          @mouseleave="handleMouseLeave('rpm-check')"
          style="cursor: pointer"
        >
          <n-progress
            type="dashboard"
            gap-position="bottom"
            :percentage="rpmCheckProgress ? rpmCheckProgress : ''"
          />
          <p>rpm check通过率</p>
        </n-gi>
        <n-gi
          id="AT"
          :span="1"
          class="item"
          @click="handleClick('AT')"
          @mouseenter="handleMouseEnter('AT')"
          @mouseleave="handleMouseLeave('AT')"
          style="cursor: pointer"
        >
          <n-progress :color="renderColor(atPassed)" type="dashboard" gap-position="bottom" :percentage="atProgress" />
          <p>最新AT通过率</p>
        </n-gi>
        <n-gi
          id="weeklybuild-health"
          :span="1"
          class="item"
          @click="handleClick('weeklybuild-health')"
          @mouseenter="handleMouseEnter('weeklybuild-health')"
          @mouseleave="handleMouseLeave('weeklybuild-health')"
          style="cursor: pointer"
        >
          <n-progress
            :color="renderColor(weeklybuildPassed)"
            type="dashboard"
            gap-position="bottom"
            :percentage="weeklybuildHealth"
          />
          <p>每周构建健康度</p>
        </n-gi>
      </n-grid>
    </n-card>
    <n-card title="每日构建记录" v-if="showCard == 'daily-build'">
      <daily-build :quality-board-id="qualityBoardId" />
    </n-card>
    <n-card title="rpm check记录" v-if="showCard == 'rpm-check'">
      <rpm-check :quality-board-id="qualityBoardId" />
    </n-card>
    <n-card title="AT历史记录" v-if="showCard == 'AT'">
      <template #header-extra>
        <n-button type="primary" ghost :loading="loadingRef" @click="exportAtHistoryFn(qualityBoardId)">
          <template #icon>
            <n-icon>
              <FileExport />
            </n-icon>
          </template>
          AT报告导出
        </n-button>
      </template>
      <at-overview :quality-board-id="qualityBoardId" />
    </n-card>
    <n-card title="每周构建记录" v-if="showCard == 'weeklybuild-health'">
      <weeklybuild-health :quality-board-id="qualityBoardId" />
    </n-card>
  </div>
</template>
<script>
import axios from '@/axios';
import { FileExport } from '@vicons/tabler';
import atOverview from './atOverview';
import dailyBuild from './dailyBuild';
import weeklybuildHealth from './weeklybuildHealth';
import rpmCheck from './rpmCheck';
import { modules } from './modules';
export default {
  components: {
    atOverview,
    dailyBuild,
    weeklybuildHealth,
    rpmCheck,
    FileExport
  },
  props: {
    qualityBoardId: Number
  },
  setup(props) {
    onMounted(() => {
      modules.getStatistic(props.qualityBoardId);
      modules.handleClick('weeklybuild-health');
    });

    onUnmounted(() => {
      modules.cleanQualityProtectData();
    });

  // 导出AT报告结果
  const loadingRef = ref(false);
    const exportAtHistoryFn = (id) => {
    loadingRef.value = true;
    let axiosUrl = `/v1/qualityboard/${id}/at-report`;
    let tag = 'report';
    axios.downLoad(axiosUrl, null, tag).then((res) => {
      let blob = new Blob([res.data], { type: 'application/vnd.ms-excel' });
      let url = URL.createObjectURL(blob);
      let alink = document.createElement('a');
      document.body.appendChild(alink);
      alink.download = decodeURIComponent(res.headers['content-disposition'].split('=')[2].slice(7));
      alink.target = '_blank';
      alink.href = url;
      alink.click();
      alink.remove();
      URL.revokeObjectURL(url);
      loadingRef.value = false;
    }).catch(()=>{
      loadingRef.value = false;
    });
  };
  
    return {
      pagenation: false,
      ...modules,
      FileExport,
      exportAtHistoryFn
    };
  }
};
</script>
<style scoped>
.item {
  text-align: center;
}
</style>
