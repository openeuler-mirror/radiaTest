<template>
  <div>
    <n-card>
      <n-grid x-gap="12" :cols="4">
        <n-gi :span="1" v-for="item in list" :key="item.id" class="item">
          <n-progress
            type="dashboard"
            gap-position="bottom"
            :percentage="item.progress"
          />
          <p>{{item.label}}</p>
        </n-gi>
        <n-gi :span="1" class="item">
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
    <n-card title="AT">
      <n-data-table />
    </n-card>
  </div>
</template>
<script>
import {ref} from 'vue';
import {CheckmarkCircleSharp,CloseCircleSharp} from '@vicons/ionicons5';
export default {
  components:{
    CheckmarkCircleSharp,
    CloseCircleSharp
  },
  setup() {
    const list = ref([
      {progress:100,label:'AT通过率',id:1},
      {progress:100,label:'周防护网',id:2},
      {progress:100,label:'rpm check',id:3},
    ]);
    const dailyBuild = ref([
      {date:'2022-09-28',success:false},
      {date:'2022-09-29',success:false},
      {date:'2022-09-30',success:true},
    ]);
    return {
      list,
      dailyBuild
    };
  },
};
</script>
<style scoped>
.item{
  text-align: center;
}
</style>
