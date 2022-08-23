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
            :color="dailyBuildCompletion === 100 ? '#18A058' : '#C20000'"
            type="dashboard"
            gap-position="bottom"
            :percentage="dailyBuildCompletion"
          />
          <p>每日构建</p>
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
          <n-progress
            :color="atProgress === 100 ? '#18A058' : '#C20000'"
            type="dashboard"
            gap-position="bottom"
            :percentage="atProgress"
          />
          <p>最新AT通过率</p>
        </n-gi>
        <n-gi 
          id="weekly-defend"
          :span="1" 
          class="item" 
          @click="handleClick('weekly-defend')"
          @mouseenter="handleMouseEnter('weekly-defend')"
          @mouseleave="handleMouseLeave('weekly-defend')"
          style="cursor: pointer"
        >
          <n-progress
            type="dashboard"
            gap-position="bottom"
            :percentage="weeklyDefendProgress"
          />
          <p>本周防护通过率</p>
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
            :percentage="rpmCheckProgress"
          />
          <p>rpm check通过率</p>
        </n-gi>
      </n-grid>
    </n-card>
    <n-card title="每日构建记录" v-if="showCard=='daily-build'">
      <daily-build :quality-board-id="qualityBoardId" />
    </n-card>
    <n-card title="AT历史记录" v-if="showCard=='AT'">
      <at-overview :quality-board-id="qualityBoardId" />
    </n-card>
    <n-card title="周防护记录" v-if="showCard=='weekly-defend'">
      <n-empty description="开发中"/>
    </n-card>
    <n-card title="rpm check记录" v-if="showCard=='rpm-check'">
      <n-empty description="开发中"/>
    </n-card>
  </div>
</template>
<script>
import {ref, onMounted} from 'vue';
import atOverview from './atOverview';
import dailyBuild from './dailyBuild';
import { modules } from './modules';
export default {
  components:{
    atOverview,
    dailyBuild,
  },
  props: {
    qualityBoardId: Number,
  },
  setup(props) {
    const rpmCheckProgress = ref(0);
    const weeklyDefendProgress = ref(0);

    onMounted(() => {
      modules.getStatistic(props.qualityBoardId);
      modules.handleClick('daily-build');
    });

    return {
      pagenation: false,
      ...modules,
      rpmCheckProgress,
      weeklyDefendProgress,
    };
  },
};
</script>
<style scoped>
.item{
  text-align: center;
}
</style>
