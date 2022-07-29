<template>
  <div>
    <n-card>
      <n-grid x-gap="12" :cols="4">
        <n-gi 
          :id="item.id"
          :span="1" 
          v-for="(item, index) in list" 
          :key="item.id" 
          class="item" 
          @click="changeNum(index)"
          @mouseenter="handleMouseEnter(item.id)"
          @mouseleave="handleMouseLeave(item.id)"
          style="cursor: pointer"
        >
          <n-progress
            type="dashboard"
            gap-position="bottom"
            :percentage="item.progress"
          />
          <p>{{item.label}}</p>
        </n-gi>
        <n-gi 
          id="dailyBuild"
          :span="1" 
          class="item" 
          @click="() => {dailyBuildShow = true;}"
          @mouseenter="handleMouseEnter('dailyBuild')"
          @mouseleave="handleMouseLeave('dailyBuild')"
          style="cursor: pointer"
        >
          <div v-for="item in dailyBuild" :key="item.id">
            <p>
              <span>{{item.date}}</span>
              <n-icon :color="item.success?'green':'red'">
                <CheckmarkCircleSharp v-if="item.success"/>
                <CloseCircleSharp v-else/>
              </n-icon>
            </p>
          </div>
          <p>每日构建</p>
        </n-gi>
      </n-grid>
    </n-card>
    <n-card v-for="(item, index) in list" :key="item.id" :title="item.label" v-show="index === num && !dailyBuildShow">
      <!--<n-data-table
        :columns="columns"
        :data="tableData"
        :pagination="pagination"
        :bordered="false"
      />-->
      <n-empty description="开发中"/>
    </n-card>
    <n-card title="每日构建" v-if="dailyBuildShow">
      <!--<n-data-table
        :columns="columns"
        :data="tableData"
        :pagination="pagination"
        :bordered="false"
      />-->
      <n-empty description="开发中"/>
    </n-card>
  </div>
</template>
<script>
import {ref, onMounted} from 'vue';
import {CheckmarkCircleSharp,CloseCircleSharp} from '@vicons/ionicons5';
import { modules } from './modules';
export default {
  components:{
    CheckmarkCircleSharp,
    CloseCircleSharp
  },
  setup() {
    const num = ref(0);
    const atProgress = ref(0);
    const weeklyDefend = ref(0);
    const rpmCheck = ref(0);
    const todayBuildResult = ref(true);
    const yesterdayBuildResult = ref(true);
    const tdbyBuildResult = ref(true);
    const dailyBuild = ref([]);
    const dailyBuildShow = ref(false);

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
    });

    function changeNum(index){
      num.value = index;
      dailyBuildShow.value = false;
      // 调取切换tab获取数据的接口
    }
    const list = ref([
      {progress: atProgress.value, label: 'AT通过率', id:1},
      {progress: weeklyDefend.value, label: '周防护网', id:2},
      {progress: rpmCheck.value, label: 'rpm check', id:3},
    ]);
    return {
      num,
      list,
      dailyBuild,
      changeNum,
      dailyBuildShow,
      pagenation: false,
      ...modules,
    };
  },
};
</script>
<style scoped>
.item{
  text-align: center;
}
</style>
