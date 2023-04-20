<template>
  <n-card
    :bordered="false"
    size="huge"
    :segmented="{
      content: 'hard'
    }"
    header-style="
      font-size: 30px;
      height: 80px;
      font-family: 'v-sans';
      padding-top: 40px;
      background-color: rgb(242,242,242);
    "
    content-style="
      padding: 0;
    "
  >
    <template #header>
      <div class="nav-header">
        <div class="nav-body">
          <ul class="nav-wrapper">
            <li v-for="(item, index) in menu" :key="index" @click="menuClick(item)">
              <template v-if="showMenuItem(item)">
                <a :class="{ active: menuSelect === item.id }">{{ item.text }}</a>
              </template>
            </li>
          </ul>
        </div>
        <div class="nav-footer">
          <div v-show="isTask" class="footer-wrapper">
            <a class="footer-item" v-show="kanban && isTask && !backable" @click="toggleView">
              <n-icon size="16"> <LayoutKanban /> </n-icon>甘特视图
            </a>
            <a class="footer-item" v-show="!kanban && isTask && !backable" @click="toggleView">
              <n-icon size="16"> <Table /> </n-icon>泳道视图
            </a>
            <a class="footer-item" v-show="isTask && backable" @click="menuClick({ name: 'task' }, 0)">
              <n-icon size="16"> <Table /> </n-icon>返回看板
            </a>
            <a class="footer-item" v-show="isTask && !backable" @click="menuClick({ name: 'distribution' }, 0)">
              <n-icon size="16"> <TextAlignDistributed20Filled /> </n-icon>分配模板管理
            </a>
            <a class="footer-item" v-show="isTask && !backable" @click="menuClick({ name: 'report' }, 0)">
              <n-icon size="16"> <BarChart /> </n-icon>可视化
            </a>
            <filterButton
              v-show="isTask && !backable"
              class="footer-item"
              :filterRule="filterRule"
              @filterchange="filterchange"
            ></filterButton>
            <a class="footer-item" v-show="isTask && !backable" @click="showRecycleBin">
              <n-icon size="16"> <Delete48Regular /> </n-icon>回收站
            </a>
            <a class="footer-item">
              <n-popover trigger="hover" placement="bottom">
                <template #trigger>
                  <n-icon size="18">
                    <QuestionCircle20Regular />
                  </n-icon>
                </template>
                <div>
                  <div class="item-wrap">
                    <div class="color-box person"></div>
                    <span>个人</span>
                  </div>
                  <div class="item-wrap">
                    <div class="color-box group"></div>
                    <span>团队</span>
                  </div>
                  <div class="item-wrap">
                    <div class="color-box organization"></div>
                    <span>组织</span>
                  </div>
                  <div class="item-wrap">
                    <div class="color-box version"></div>
                    <span>版本</span>
                  </div>
                </div>
              </n-popover>
            </a>
          </div>
          <div class="footer-wrapper" v-show="isDesign">
            <a class="footer-item" v-show="!isDesignTemplate" @click="isDesignTemplate = true">
              <n-icon size="16"> <Template /> </n-icon>测试策略模板库
            </a>
            <a class="footer-item" v-show="isDesignTemplate" @click="isDesignTemplate = false">
              <n-icon size="16"> <ArrowBackCircleOutline /> </n-icon>返回测试设计
            </a>
          </div>
        </div>
      </div>
    </template>
    <template #default>
      <div class="recycleWrap">
        <n-modal v-model:show="showRecycleBinModal">
          <n-card style="width: 1200px" title="查看回收站" :bordered="false" size="huge">
            <n-data-table
              remote
              ref="recycleBinTaskTable"
              :loading="recycleBinTaskLoading"
              :columns="recycleBinTaskColumns"
              :data="recycleBinTaskData"
              :pagination="recycleBinTaskPagination"
              @update:page="recycleBinTablePageChange"
            />
          </n-card>
        </n-modal>
      </div>
      <n-dialog-provider>
        <router-view></router-view>
      </n-dialog-provider>
    </template>
  </n-card>
</template>

<script>
import { LayoutKanban, Table } from '@vicons/tabler';
import { Template } from '@vicons/carbon';
import { BarChart, ArrowBackCircleOutline } from '@vicons/ionicons5';
import { QuestionCircle20Regular, Delete48Regular, TextAlignDistributed20Filled } from '@vicons/fluent';
import { modules } from './modules/index';
import { useRoute } from 'vue-router';
import filterButton from '@/components/filter/filterButton.vue';

export default defineComponent({
  components: {
    LayoutKanban,
    Table,
    QuestionCircle20Regular,
    Delete48Regular,
    filterButton,
    TextAlignDistributed20Filled,
    BarChart,
    Template,
    ArrowBackCircleOutline
  },
  setup() {
    const route = useRoute();

    const showMenuItem = (item) => {
      if (item.name !== 'testing') {
        if (window.atob(route.params?.workspace).search('group') !== -1) {
          return false;
        }
        return true;
      }
      return true;
    };

    watch(() => route.path, modules.watchRoute);
    onMounted(() => {
      modules.watchRoute();
      modules.initCondition();
    });

    return {
      showMenuItem,
      ...modules
    };
  }
});
</script>

<style scoped lang="less">
.nav-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.nav-body {
  position: relative;
  white-space: nowrap;
  z-index: 1;
  display: -ms-flexbox;
  display: -webkit-box;
  display: flex;
  -ms-flex-pack: center;
  -webkit-box-pack: center;
  justify-content: center;

  .nav-wrapper {
    position: relative;
    border: none;
    list-style-type: none;
    padding: 0;

    li {
      list-style: none;
      float: left;
      z-index: 2;
      padding: 0 20px;

      a {
        display: inline-block;
        position: relative;
        margin: 0;
        color: #383838;
        font-size: 15px;
        font-weight: 400;
        cursor: pointer;
        border-bottom: 3px solid #fafafa;

        &.active {
          border-bottom: 3px solid #3da8f5;
        }
      }
    }
  }
}

.nav-footer {
  position: relative;
  display: -webkit-box;
  display: -ms-flexbox;
  display: flex;
  justify-content: flex-end;
  -webkit-box-align: center;
  -ms-flex-align: center;
  align-items: center;
  z-index: 998;

  .footer-wrapper {
    display: flex;

    .footer-item {
      font-size: 14px;
      position: relative;
      padding: 15px 10px;
      margin: 0 5px;
      display: flex;
      align-items: center;
      text-align: center;
      cursor: pointer;
      &:hover {
        color: #3da8f5;
      }
    }
  }
}

.item-wrap {
  display: flex;
  justify-content: space-evenly;
  align-items: center;

  .color-box {
    width: 28px !important;
    height: 15px !important;
    margin-right: 5px;
  }

  .person {
    background: #3da8f5;
  }

  .group {
    background: #ff8040;
  }

  .organization {
    background: #00ec00;
  }

  .version {
    background: #8000ff;
  }
}
</style>
