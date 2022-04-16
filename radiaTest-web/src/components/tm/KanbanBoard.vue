<template>
  <div class="board">
    <div class="header">
      <div class="stage-name">
        <div v-if="showStatusItem" class="left">
          <div>
            <span>{{ taskData.statusItem }}</span>
            <span> · </span>
            <span>{{ taskData.tasks.length }}</span>
          </div>
          <div v-if="taskData.statusItem === '已完成'">
            <n-switch
              v-model:value="showTaskList"
              size="small"
              @update:value="handleChange"
            >
              <template #checked>全任务</template>
              <template #unchecked>仅本人</template>
            </n-switch>
          </div>
        </div>
        <div v-else>
          <div class="inputWrap">
            <n-input
              v-model:value="statusItemValue"
              type="text"
              placeholder="请输入新的状态名"
            />
          </div>
          <div class="btnWrap">
            <n-button type="error" ghost @click="cancelStatusItem"
              >取消</n-button
            >
            <n-button type="info" ghost @click="editStatusItem">确定</n-button>
          </div>
        </div>
      </div>
      <div class="dots">
        <a>
          <n-dropdown :options="options" @select="select">
            <n-icon size="14">
              <Dots />
            </n-icon>
          </n-dropdown>
        </a>
      </div>
    </div>
    <n-scrollbar style="max-height: 840px;">
      <div class="main">
        <div class="stage-tasks">
          <draggable
            class="list-group"
            :list="taskData.tasks"
            :animation="200"
            group="taskGroup"
            @change="dragChange"
            itemKey="id"
            filter=".forbid"
          >
            <template #item="{ element }">
              <div class="list-group-item" :class="isDrag(element)">
                <div class="task-card">
                  <div
                    class="task-priority"
                    :style="{ backgroundColor: tagColor(element.type) }"
                  ></div>
                  <div class="task-main">
                    <div class="task-content-wrapper">
                      <div class="task-content" @click="taskDetail(element)">
                        {{ element.title }}
                      </div>
                      <img
                        class="avatar"
                        :src="element.creator.avatar_url"
                      />
                    </div>
                    <div
                      class="task-info-wrapper"
                      v-show="element?.tasks?.length"
                    >
                      <div class="task-infos">
                        <span class="icon-wrapper">
                          <n-icon size="14">
                            <TextBulletListLtr20Filled />
                          </n-icon>
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </draggable>
        </div>
        <div class="task-creator" v-show="taskData.statusItem === '待办中'">
          <a @click="showCreateTask">
            <n-icon size="16">
              <AddCircle24Regular />
            </n-icon>
            <span>添加任务</span>
          </a>
        </div>
      </div>
    </n-scrollbar>
    <n-modal v-model:show="deleteTasksModal">
      <n-card
        style="width: 600px"
        title="批量删除任务"
        :bordered="false"
        size="huge"
      >
        <div style="display:flex;">
          <n-select
            placeholder="请选择任务"
            style="width:70%"
            multiple
            v-model:value="deleteTasksValue"
            :options="deleteTasksOption"
          />
          <div style="width:30%;display:flex;justify-content:space-evenly;">
            <n-button type="error" ghost @click="cancelDeleteTasks"
              >取消</n-button
            >
            <n-button
              type="info"
              ghost
              @click="deleteTasksBtn(deleteTasksValue)"
              >删除</n-button
            >
          </div>
        </div>
      </n-card>
    </n-modal>
  </div>
</template>

<script>
import { h } from 'vue';
import { Dots } from '@vicons/tabler';
import {
  AddCircle24Regular,
  TextBulletListLtr20Filled,
  Delete20Regular,
  Edit24Regular,
} from '@vicons/fluent';
import { NIcon } from 'naive-ui';
import draggable from 'vuedraggable';

const renderIcon = (icon) => {
  return () => {
    return h(NIcon, null, {
      default: () => h(icon),
    });
  };
};

export default {
  components: {
    Dots,
    TextBulletListLtr20Filled,
    AddCircle24Regular,
    draggable,
  },
  props: ['taskData'],
  emits: ['showDetail', 'toggleComplete'],
  data() {
    return {
      options: [
        {
          label: '编辑状态',
          key: 'edit',
          icon: renderIcon(Edit24Regular),
        },
        {
          label: '删除状态',
          key: 'delete',
          icon: renderIcon(Delete20Regular),
        },
        {
          label: '批量删除任务',
          key: 'deleteTasks',
          disabled: this.taskData.statusItem !== '待办中',
          icon: renderIcon(Delete20Regular),
        },
      ],
      showStatusItem: true,
      statusItemValue: null,
      deleteTasksModal: false,
      deleteTasksValue: null,
      deleteTasksOption: [],
      showTaskList: true,
    };
  },
  methods: {
    select(key) {
      if (key === 'delete') {
        this.$emit('select', { key });
      } else if (key === 'edit') {
        this.showStatusItem = false;
      } else if (key === 'deleteTasks') {
        this.deleteTasksModal = true;
        if (this.taskData.tasks) {
          this.deleteTasksValue = null;
          this.deleteTasksOption = this.taskData.tasks.map((v) => {
            return {
              label: v.title,
              value: v.id,
            };
          });
        }
      }
    },
    editStatusItem() {
      this.$emit('select', { key: 'edit', value: this.statusItemValue });
    },
    cancelStatusItem() {
      this.showStatusItem = true;
    },
    showCreateTask() {
      this.$store.commit('taskManage/toggleNewTaskDrawer');
      this.$emit('createTask');
    },
    taskDetail(element) {
      this.$emit('showDetail', element);
    },
    tagColor(type) {
      let bgColor = '';
      switch (type) {
        case 'PERSON':
          bgColor = '#3da8f5';
          break;
        case 'GROUP':
          bgColor = '#ff8040';
          break;
        case 'ORGANIZATION':
          bgColor = '#00ec00';
          break;
        case 'VERSION':
          bgColor = '#8000ff';
          break;
        default:
          bgColor = 'white';
      }
      return bgColor;
    },
    dragChange(e) {
      if (e.added) {
        this.$emit('changeStatus', e.added.element);
      }
    },
    isDrag(element) {
      if (
        !element.has_milestone ||
        element.status.name === '已完成' ||
        (element.status.name === '执行中' && !element.auto_case_success)
      ) {
        return 'forbid';
      }
      return '';
    },
    cancelDeleteTasks() {
      this.deleteTasksModal = false;
    },
    deleteTasksBtn() {
      this.$emit('select', {
        key: 'deleteTasks',
        value: this.deleteTasksValue,
      });
      this.deleteTasksModal = false;
    },
    handleChange(value) {
      this.$emit('toggleComplete', value);
    },
  },
};
</script>

<style lang="less" scoped>
.board {
  position: relative;
  // height: 100%;
  height: 890px;
  width: 295px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  margin-right: 10px;
  vertical-align: top;
  border-radius: 3px;
  box-sizing: border-box;
  background-color: #f5f6f8;

  .header {
    padding: 14px 14px;
    font-size: 14px;
    cursor: move;
    display: flex;
    flex: 0 0 auto;
    flex-direction: row;
    align-items: center;
    font-weight: 700;
    z-index: 1;
    justify-content: space-between;

    .stage-name {
      box-sizing: border-box;
      width: 90%;

      .left {
        display: flex;
        justify-content: space-between;
      }

      .btnWrap {
        display: flex;
        justify-content: space-evenly;
        margin-top: 5px;
      }
    }

    .dots {
      position: absolute;
      right: 15px;
      box-sizing: border-box;

      a {
        color: grey;
        text-decoration: none;
        cursor: pointer;
        &:hover {
          color: #3da8f5;
        }
      }
    }
  }

  .main {
    // height: 890px;
    width: 100%;
    padding: 0px;
    position: relative;
    flex: 1;
    overflow: auto;
    overflow-x: visible;

    .stage-tasks {
      opacity: 1;
      min-height: 5px;
      padding: 0 5px;
      position: relative;

      .list-group-item {
        .task-card {
          // border-left: 3px solid #fff;
          margin: 0 8px 8px;
          display: flex;
          position: relative;
          background-color: #fff;
          height: 50px;
          align-items: center;

          .task-priority {
            opacity: 1;
            border-bottom-left-radius: 3px;
            border-top-left-radius: 3px;
            position: absolute;
            top: 0;
            bottom: 0;
            left: 0;
            width: 6px;
            cursor: pointer;
            height: 100%;
          }

          .check-box-wrapper {
            display: flex;
            align-items: center;
            text-align: center;
            margin: 7px 6px 0 6px;
            justify-content: center;
            border-radius: 3px;
            cursor: pointer;
          }

          .task-main {
            margin-left: 15px;
            width: 100%;

            .task-content-wrapper {
              overflow: hidden;
              min-height: 24px;
              flex: 1 1 auto;
              display: flex;
              flex-direction: row;
              align-items: center;

              .task-content {
                margin: 2px 12px 0 0;
                padding: 0;
                border: none;
                background: none;
                cursor: pointer;
                word-wrap: break-word;
                overflow: hidden;
                flex: 1 1 auto;
                width: 200px;
              }

              .avatar {
                opacity: 1;
                margin: 0 14px 0 0;
                flex: 0 0 auto;
                background-size: cover !important;
                background-repeat: no-repeat !important;
                background-position: 50% !important;
                border-radius: 50%;
                display: inline-block;
                background-color: #eee;
                width: 24px;
                height: 24px;
                vertical-align: middle;
                border-style: none;
              }
            }

            .task-info-wrapper {
              display: flex;
              padding-right: 14px;
              .task-infos {
                flex: 1 1 auto;
                overflow: hidden;
                line-height: 20px;
                font-size: 0;
                .icon-wrapper {
                  overflow: hidden;
                  text-overflow: ellipsis;
                  white-space: nowrap;
                  font-size: 14px;
                  display: inline-flex;
                  align-items: center;
                  height: 20px;
                  vertical-align: middle;
                  max-width: 100%;
                  color: rgba(0, 0, 0, 0.45);
                }
              }
            }
          }
        }
      }
    }

    .task-creator {
      background: #fff;
      height: auto;
      margin: 0 12px;
      width: 270px;
      border-radius: 3px;
      display: flex;
      justify-content: center;
      flex-direction: row;
      align-items: center;
      margin-bottom: 10px;

      a {
        padding: 5px 15px;
        font-size: 14px;
        color: #a6a6a6;
        border-radius: 3px;
        display: flex;
        justify-content: center;
        align-items: center;
        cursor: pointer;
        vertical-align: middle;

        &:hover {
          color: #3da8f5;
        }
      }
    }
  }
}
</style>
