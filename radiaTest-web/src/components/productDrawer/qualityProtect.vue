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
      <at-overview :quality-board-id="qualityBoardId" />
    </n-card>
    <n-card title="每周构建记录" v-if="showCard == 'weeklybuild-health'">
      <weeklybuild-health :quality-board-id="qualityBoardId" />
    </n-card>
  </div>
</template>
<script>
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
    rpmCheck
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

    return {
      pagenation: false,
      ...modules
    };
  }
};
</script>
<style scoped>
.item {
  text-align: center;
}
</style>
