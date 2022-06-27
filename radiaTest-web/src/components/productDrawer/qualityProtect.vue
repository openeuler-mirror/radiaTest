<template>
  <div>
    <n-card>
      <n-grid x-gap="12" :cols="4">
        <n-gi :span="1" v-for="(item, index) in list" :key="item.id" class="item" @click="changeNum(index)" style="cursor: pointer">
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
    <n-card v-for="(item, index) in list" :key="item.id" :title="item.label" v-show="index === num">
      <n-data-table
        :columns="columns"
        :data="tableData"
        :pagination="pagination"
        :bordered="false"
      />
    </n-card>
  </div>
</template>
<script>
import {ref} from 'vue';
import {CheckmarkCircleSharp,CloseCircleSharp} from '@vicons/ionicons5';
import { modules } from './modules';
export default {
  components:{
    CheckmarkCircleSharp,
    CloseCircleSharp
  },
  setup() {
    const num = ref(0);
    function changeNum(index){
      num.value = index;
      // 调取切换tab获取数据的接口
    }
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
      num,
      list,
      dailyBuild,
      changeNum,
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
