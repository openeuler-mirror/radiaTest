<template>
  <div class="historyVersionBox">
    <div class="filter-aside">
      <div>
        <n-input
          class="filter-item"
          v-model:value="searchTitle"
          placeholder="请输入"
          @change="getData"
        />
        <n-date-picker
          class="filter-item"
          v-model:value="timeRange"
          type="daterange"
          @change="getData"
        />
      </div>
      <div v-for="(item, index) in versionList" :key="index">
        <n-alert
          :class="['alertButton', activeId === item.commit_id ? 'active' : '']"
          :title="item.title"
          type="success"
          @click="handleSelectCase(item.commit_id)"
        >
          <template #header>
            <n-h4 style="word-wrap: break-word">
              {{ item.title }}
            </n-h4>
          </template>
          版本:{{ item.version }}
        </n-alert>
      </div>
    </div>
    <div class="table-aside">
      <collapse-list :list="detailsList" @edit="edit" v-if="showDetails" />
      <div
        v-else
        style="
              height: 100%;
              display: flex;
              justify-content: center;
              align-items: center;
            "
      >
        <n-empty description="请选择要查看的历史信息"> </n-empty>
      </div>
    </div>
  </div>
</template>
<script>
import { modules } from './historicalVersionModules';
import collapseList from '@/components/collapseList/collapseList.vue';
export default {
  components: {
    collapseList,
  },
  setup() {
    return {
      ...modules,
    };
  },
  mounted() {
    this.getData();
  },
};
</script>
<style lang="less" scoped>
.active {
  box-shadow: 0 4px 20px 4px rgba(0, 0, 0, 0.4) !important;
}
.alertButton {
  box-shadow: 0 4px 36px 0 rgba(190, 196, 204, 0.2);
  margin-bottom: 40px;
}
.alertButton:hover {
  cursor: pointer;
  box-shadow: 0 4px 20px 4px rgba(0, 0, 0, 0.4) !important;
}
.historyVersionBox {
  display: flex;
  .filter-aside {
    flex: 3;
    padding-right: 32px;
    .filter-item {
      margin: 10px 0;
    }
  }
  .table-aside {
    flex: 7;
  }
}
</style>
