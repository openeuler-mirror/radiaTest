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
          <div v-for="item in dailyBuild" :key="item.id">
            <p>
              <span>{{item.date}}</span>
              <n-icon :color="item.success?'#18A058':'red'">
                <CheckmarkCircleSharp v-if="item.success"/>
                <CloseCircleSharp v-else/>
              </n-icon>
            </p>
          </div>
          <p style="margin-top: 25px;">每日构建</p>
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
            color="#18A058"
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
      <n-empty description="开发中"/>
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
import {CheckmarkCircleSharp,CloseCircleSharp} from '@vicons/ionicons5';
import atOverview from './atOverview';
import { modules } from './modules';
export default {
  components:{
    atOverview,
    CheckmarkCircleSharp,
    CloseCircleSharp
  },
  props: {
    qualityBoardId: Number,
  },
  setup(props) {
    const rpmCheckProgress = ref(0);
    const weeklyDefendProgress = ref(0);
    const todayBuildResult = ref(true);
    const yesterdayBuildResult = ref(true);
    const tdbyBuildResult = ref(true);
    const dailyBuild = ref([]);

    onMounted(() => {
      const date = new Date();
      const today = `${date.getFullYear()}-${date.getMonth()+1}-${date.getDate()}`;
      date.setTime(date.getTime()-(24*60*60*1000));
      const yesterday = `${date.getFullYear()}-${date.getMonth()+1}-${date.getDate()}`;
      date.setTime(date.getTime()-(24*60*60*1000));
      const tdby = `${date.getFullYear()}-${date.getMonth()+1}-${date.getDate()}`;

      dailyBuild.value = [
        {date: today, success: todayBuildResult.value},
        {date: yesterday, success: yesterdayBuildResult.value},
        {date: tdby, success: tdbyBuildResult.value},
      ];

      modules.getStatistic(props.qualityBoardId);
      modules.handleClick('daily-build');
    });

    return {
      dailyBuild,
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
