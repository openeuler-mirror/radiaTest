<template>
  <n-card
    title="任务管理"
    size="huge"
    :segmented="{
      content: 'hard',
    }"
    header-style="
            font-size: 30px;
            height: 80px;
            font-family: 'v-sans';
            padding-top: 40px;
            background-color: rgb(242,242,242);
        "
    style="height: 100%"
  >
    <template #header>
      <n-grid :cols="3">
        <n-gi class="nav-header">任务管理</n-gi>
        <n-gi class="nav-body">
          <ul class="nav-wrapper">
            <li
              v-for="(item, index) in menu"
              :key="index"
              @click="menuClick(item, index)"
            >
              <a :class="{ active: menuSelect == index }">{{ item.text }}</a>
            </li>
          </ul>
        </n-gi>
        <n-gi class="nav-footer">
          <div v-show="isTask" class="footer-wrapper">
            <a class="footer-item" v-show="kanban" @click="toggleView">
              <n-icon size="16">
                <LayoutKanban /> </n-icon
              >表格视图
            </a>
            <a class="footer-item" v-show="!kanban" @click="toggleView">
              <n-icon size="16">
                <Table /> </n-icon
              >看板视图
            </a>
            <a class="footer-item" @click="screen">
              <n-icon size="16">
                <Search /> </n-icon
              >筛选
            </a>
            <a class="footer-item" @click="showRecycleBin">
              <n-icon size="16">
                <Delete48Regular /> </n-icon
              >回收站
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
        </n-gi>
      </n-grid>
    </template>
    <template #default>
      <div id="drawer-target"></div>
      <n-drawer v-model:show="active" to="#drawer-target" width="324px">
        <n-drawer-content title="筛选" closable>
          <n-form
            :model="model"
            :rules="rules"
            ref="formRef"
            label-placement="left"
            :label-width="80"
            size="medium"
            :style="{}"
          >
            <n-form-item label="名称" path="title">
              <n-input
                placeholder="请输入任务名称"
                v-model:value="model.title"
              />
            </n-form-item>
            <n-form-item label="类型" path="type">
              <n-select
                placeholder="请选择"
                clearable
                :options="taskTypeOptions"
                v-model:value="model.type"
              />
            </n-form-item>
            <n-form-item label="创建者" path="originator">
              <n-select
                clearable
                placeholder="请选择"
                :options="originators"
                v-model:value="model.originator"
              />
            </n-form-item>
            <n-form-item label="执行者" path="executor_id">
              <n-select
                placeholder="请选择"
                clearable
                :options="executors"
                v-model:value="model.executor_id"
              />
            </n-form-item>
            <n-form-item label="协助人" path="participant_id">
              <n-select
                placeholder="请选择"
                :options="participants"
                clearable
                v-model:value="model.participant_id"
                multiple
              />
            </n-form-item>
            <n-form-item label="状态" path="status_id">
              <n-select
                placeholder="请选择"
                clearable
                :options="statusOptions"
                v-model:value="model.status_id"
              />
            </n-form-item>
            <n-form-item label="截止日期" path="deadline">
              <n-date-picker type="date" v-model:value="model.deadline" />
            </n-form-item>
            <n-form-item label="开始日期" path="start_time">
              <n-date-picker type="date" v-model:value="model.start_time" />
            </n-form-item>
            <div class="searchButtonBox">
              <n-button class="btn" type="error" ghost @click="clearCondition"
                >重置</n-button
              >
              <n-button
                class="btn"
                type="info"
                ghost
                @click="handleValidateButtonClick"
                >搜索</n-button
              >
            </div>
          </n-form>
        </n-drawer-content>
      </n-drawer>
      <div class="recycleWrap">
        <n-modal v-model:show="showRecycleBinModal">
          <n-card
            style="width: 1200px"
            title="查看回收站"
            :bordered="false"
            size="huge"
          >
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
    <template #action>
      <n-divider />
      <div
        style="
          text-align: center;
          color: grey;
          padding-top: 15px;
          padding-bottom: 0;
        "
      >
        {{ `${config.name} ${config.version}·${config.license}` }}
      </div>
    </template>
  </n-card>
</template>

<script>
import { defineComponent, onMounted, watch } from 'vue';
import { LayoutKanban, Table, Search } from '@vicons/tabler';
import { QuestionCircle20Regular, Delete48Regular } from '@vicons/fluent';
import { modules } from './modules/index';
import { useRoute } from 'vue-router';
import config from '@/assets/config/settings';

export default defineComponent({
  components: {
    LayoutKanban,
    Table,
    Search,
    QuestionCircle20Regular,
    Delete48Regular,
  },
  setup() {
    const route = useRoute();
    watch(
      () => route.path,
      () => {
        if (route.path === '/home/tm/task') {
          modules.menuSelect.value = 0;
          modules.isTask.value = true;
        } else if (route.path === '/home/tm/report') {
          modules.menuSelect.value = 1;
          modules.isTask.value = false;
        } else if (route.path === '/home/tm/distribution') {
          modules.menuSelect.value = 2;
          modules.isTask.value = false;
        }
      }
    );
    onMounted(() => {
      modules.taskTypeOptions.value = [
        { label: '个人任务', value: 'PERSON' },
        { label: '团队任务', value: 'GROUP' },
        { label: '组织任务', value: 'ORGANIZATION' },
        { label: '版本任务', value: 'VERSION' },
      ];
      modules.initCondition();
    });

    return {
      config,
      ...modules,
    };
  },
  beforeRouteEnter(to) {
    if (to.path === '/home/tm/task') {
      modules.menuSelect.value = 0;
      modules.isTask.value = true;
    } else if (to.path === '/home/tm/report') {
      modules.menuSelect.value = 1;
      modules.isTask.value = false;
    } else if (to.path === '/home/tm/distribution') {
      modules.menuSelect.value = 2;
      modules.isTask.value = false;
    }
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
    background: #00ec00;
  }

  .version {
    background: #8000ff;
  }
}
</style>
