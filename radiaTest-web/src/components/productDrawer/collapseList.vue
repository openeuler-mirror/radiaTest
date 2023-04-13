<template>
  <n-collapse @item-header-click="itemHeaderClick">
    <n-collapse-item v-for="item in treeList" :key="item.id" :title="item.title" :name="item.id">
      <collapseList
        v-if="childrenList[item.id] && childrenList[item.id][0]?.type !== 'case'"
        :treeList="childrenList[item.id]"
      />
      <template v-else>
        <div class="case-item" v-for="(it, ix) in childrenList[item.id]" :key="ix">
          <n-grid x-gap="12" :cols="10">
            <n-gi span="8" style="margin-left: 40px">
              {{ it.title }}
            </n-gi>
            <n-gi span="1">
              <n-icon :size="24" class="myIcon">
                <ChevronDownCircle v-if="it.result === 'success'" class="success" />
                <CloseCircle v-else-if="it.result === 'failed'" class="failed" />
                <Pending v-else-if="it.result === 'pending'" class="pending" />
                <RunningWithErrorsFilled v-else-if="it.result === 'running'" class="running" />
              </n-icon>
            </n-gi>
          </n-grid>
        </div>
      </template>
      <template v-if="item?.progress" #header-extra style="width: 70%">
        <div class="headerExtra">
          <custom-progress :progress="item.progress"> </custom-progress>
        </div>
      </template>
    </n-collapse-item>
  </n-collapse>
</template>

<script setup>
import { ChevronDownCircle, CloseCircle } from '@vicons/ionicons5';
import { Pending } from '@vicons/carbon';
import { RunningWithErrorsFilled } from '@vicons/material';
import customProgress from '@/components/customProgress/customProgress.vue';
import { getMilestoneProgressCaseNode } from '@/api/get.js';

const props = defineProps(['treeList']);
const { treeList } = toRefs(props);
const childrenList = ref({}); // 子节点
const defaultMilestoneId = inject('defaultMilestoneId');

const exchangeProgress = (progress) => {
  let obj = {};
  obj.total = progress.all_cnt;
  obj.failure = progress.failed;
  obj.block = progress.pending;
  obj.success = progress.success;
  obj.running = progress.running;
  return obj;
};

const itemHeaderClick = ({ name, expanded }) => {
  if (expanded === true) {
    getMilestoneProgressCaseNode(defaultMilestoneId.value, name).then((res) => {
      childrenList.value[name] = [];
      res.data?.children?.forEach((v) => {
        childrenList.value[name].push({
          title: v.title,
          progress: v.test_progress ? exchangeProgress(v.test_progress) : null,
          id: v.id,
          type: v.type,
          result: v.result
        });
      });
    });
  }
};
</script>

<style lang="less" scoped>
.case-item {
  align-items: center;

  .myTitle {
    text-align: center;
  }

  .myIcon {
    .success {
      color: green;
    }

    .failed {
      color: red;
    }

    .pending {
      color: gray;
    }

    .running {
      color: #2080f0;
    }
  }
}

:deep(.n-collapse-item__header-extra) {
  width: 80%;
}
.headerExtra {
  flex-grow: 1;
}
</style>
