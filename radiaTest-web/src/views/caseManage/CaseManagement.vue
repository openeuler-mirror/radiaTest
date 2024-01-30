<template>
  <!-- <n-card
    :bordered="false"
    size="huge"
    :segmented="{
      content: 'hard',
    }"
    style="height: 100%"
    content-style="padding:0"
    header-style="
            font-size: 30px;
            height: 80px;
            font-family: 'v-sans';
            background-color: rgb(242,242,242);
        "
    v-if="$route.params.workspace==='default'"
  > -->
  <n-card
    :bordered="false"
    size="huge"
    :segmented="{
      content: 'hard',
    }"
    style="height: 100%"
    content-style="padding:0"
    header-style="
            font-size: 30px;
            height: 80px;
            font-family: 'v-sans';
            background-color: rgb(242,242,242);
        "
  >
    <template #header>
      <n-grid :cols="3">
        <n-gi class="nav-header"></n-gi>
        <n-gi class="nav-body">
          <ul class="nav-wrapper">
            <li v-for="(item, index) in menu" :key="index" @click="menuClick(item, index)">
              <a :class="{ active: isTabActive(item.name) }">{{ item.text }}</a>
            </li>
          </ul>
        </n-gi>
        <n-gi class="nav-footer">
          <div class="footer-wrapper">
            <a class="footer-item" v-show="!tableView" @click="toggleView">
              <n-icon size="16"> <Table24Regular /> </n-icon>表格视图
            </a>
            <a class="footer-item" v-show="tableView" @click="toggleView">
              <n-icon size="16"> <Folder20Regular /> </n-icon>目录视图
            </a>
            <a class="footer-item" @click="showRecycleBin">
              <n-icon size="16">
                <Delete48Regular />
              </n-icon>
              回收站
            </a>
            <a class="footer-item">
              <n-popover trigger="hover" placement="bottom">
                <template #trigger>
                  <n-icon size="18">
                    <QuestionCircle20Regular />
                  </n-icon>
                </template>
                <div>
                  <div class="item-wrap">缺省</div>
                </div>
              </n-popover>
            </a>
          </div>
        </n-gi>
      </n-grid>
    </template>
    <template #default>
      <div class="recycleWrap">
        <n-modal v-model:show="showRecycleBinModal">
          <n-card style="width: 1200px" title="用例回收站" :bordered="false" size="huge">
            <n-data-table
              remote
              ref="recycleBinCaseTable"
              :loading="recycleBinCaseLoading"
              :columns="recycleBinCaseColumns"
              :data="recycleBinCaseData"
              :pagination="recycleBinCasePagination"
              @update:page="recycleBinTablePageChange"
            />
          </n-card>
        </n-modal>
      </div>
      <router-view></router-view>
    </template>
  </n-card>
  <n-card
    :bordered="false"
    size="huge"
    :segmented="{
      content: 'hard',
    }"
    style="height: 100%"
    content-style="padding:0"
    v-if="$route.params.workspace === 'release'"
  >
    <template #default>
      <router-view></router-view>
    </template>
  </n-card>
</template>

<script>
import { defineComponent } from 'vue';
import {
  QuestionCircle20Regular,
  Delete48Regular,
  Folder20Regular,
  Table24Regular,
} from '@vicons/fluent';

import manage from './modules/management.js';
import view from './modules/view.js';
export default defineComponent({
  components: {
    QuestionCircle20Regular,
    Delete48Regular,
    Folder20Regular,
    Table24Regular,
  },
  mounted() {
    this.tableView = this.$route.path.indexOf('folderview') === -1;
    this.setMenu();
  },
  setup() {
    return {
      ...view,
      ...manage,
    };
  },
});
</script>

<style scoped lang="less">
.nav-header {
  display: flex;
  align-items: center;
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

#drawer-target {
  .searchButtonBox {
    display: flex;
    justify-content: space-evenly;

    .btn {
      width: 100px;
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
    background: #4a38e6;
  }

  .version {
    background: #8000ff;
  }
}
</style>
