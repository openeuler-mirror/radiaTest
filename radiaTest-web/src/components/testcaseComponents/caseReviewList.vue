<template>
  <template v-if="dataList.length">
    <testReviewItem
      v-for="(item, index) in dataList"
      :key="index"
      :info="item"
      :options="options"
      @selectAction="handleAction"
    />
  </template>
  <n-empty style="height:300px" description="暂无数据" v-else> </n-empty>
  <div style="padding:10px 0;display:flex;justify-content:center">
    <n-pagination
      :page="page"
      :page-count="pageCount"
      @update:page="pageChange"
    />
  </div>
</template>
<script>
import testReviewItem from '@/components/testcaseComponents/testReviwItem.vue';
import { renderIcon } from '@/assets/utils/icon';
import { Close } from '@vicons/ionicons5';
import {
  Delete24Regular,
  ArrowBounce16Filled,
} from '@vicons/fluent';
import {modifyCommitStatus} from '@/api/put';
import {deleteCommit} from '@/api/delete';
export default {
  components:{
    testReviewItem
  },
  props:['dataList','page','pageCount'],
  data(){
    return {
      options:[
        {
          label: '撤回提交',
          key: 'pending',
          icon: renderIcon(ArrowBounce16Filled, 'blue'),
        },
        {
          label: '关闭提交',
          key: 'rejected',
          icon: renderIcon(Close, 'red'),
        },
        {
          label: '删除提交',
          key: 'delete',
          icon: renderIcon(Delete24Regular, 'red'),
        },
      ]
    };
  },
  methods:{
    handleAction({key,info}){
      if(key !== 'delete'){
        modifyCommitStatus(info.id,{status:key}).then(()=>{
          this.$emit('update');
        });
      }else{
        deleteCommit(info.id).then(()=>{
          this.$emit('update');
        });
      }
    },
    pageChange(page){
      this.$emit('change',page);
    }
  },
};
</script>
