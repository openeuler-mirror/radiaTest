<template>
  <div class="root-container">
    <div class="body-container">
      <div class="summary-container">
        <div class="hovered-card">
          <n-thing>
            <template #header>
              <span class="title">当前进展</span>
            </template>
            <template #header-extra>
              <p class="subtitle" v-if="item.acceptor">
                <span>{{ item.acceptor.type === 'group' ? '责任团队' : '责任人' }}:</span>
                <span>{{ item.acceptor.name }}</span>
                <span>开始时间:</span>
                <span>{{ item.acceptor.start_time }}</span>
                <span>预计完成时间:</span>
                <span>{{ item.acceptor.estimated_finish_time }}</span>
              </p>
            </template>
            <template #default>
              <div class="body">
                <n-progress
                  type="line"
                  :percentage="requireProgress[0]?.percentage"
                  :height="24"
                  :border-radius="4"
                  :fill-border-radius="0"
                />
              </div>
            </template>
          </n-thing>
        </div>
      </div>
      <div class="detail-container">
        <div class="hovered-card" style="border-radius: none;">
          <n-data-table 
            :columns="columns"
            :data="packageList"
          />
        </div>
      </div>
    </div>
    <div class="sider-container">
      <div class="hovered-card" style="padding: 10px; 20px;">
        <div ref="progressRef" class="progress-container">
          <timeline class="timeline-container">
            <timeline-item
              v-for="(item, index) in requireProgress"
              :key="index"
              :leftWidth="progressRef?.clientWidth - 60"
              :title="`进展${item.percentage}%`"
              :content="item.content"
              :time="item.create_time"
              :type="item.type"
            >
              <n-space>
                <n-tooltip trigger="hover">
                  <template #trigger>
                    <n-button text @click="handleProgressEditClick(item)">
                      <n-icon :size="14">
                        <edit />
                      </n-icon>
                    </n-button>
                  </template>
                  编辑
                </n-tooltip>
                <n-tooltip trigger="hover">
                  <template #trigger>
                    <n-button text @click="handleProgressDeleteClick(item)">
                      <n-icon :size="14">
                        <delete />
                      </n-icon>
                    </n-button>
                  </template>
                  删除
                </n-tooltip>
              </n-space>
            </timeline-item>
          </timeline>
        </div>
        <n-button 
          type="warning" 
          size="small" 
          style="width: 100%; margin-top: 10px;"
          @click="() => { postModalShow = true; }"
          :disabled="item.status !== 'accepted'"
        >
          反馈进展
        </n-button>
        <n-modal 
          v-model:show="postModalShow"
          title="反馈进展"
          preset="dialog"
          positive-text="提交"
          negative-text="取消"
          @positive-click="postSubmitCallback"
          @negative-click="postCancelCallback"
        >
          <n-space vertical style="margin-top: 20px; gap: 20px">
            <n-radio-group v-model:value="postModel.type">
              <n-space>
                <n-radio label="INFO" value="info" />
                <n-radio label="SUCCESS" value="success" />
                <n-radio label="WARNING" value="warning" />
                <n-radio label="ERROR" value="error" />
              </n-space>
            </n-radio-group>
            <div>
              <n-input-number 
                v-model:value="postModel.percentage" 
                size="small"
                :step="10"
                :max="100"
              >
                <template #suffix>
                  %
                </template>
              </n-input-number>
            </div>
            <n-form ref="formRef" :model="postModel">
              <n-form-item path="content" label="进展描述">
                <n-input
                  v-model:value="postModel.content"
                  type="textarea"
                  :autosize="{
                    minRows: 3,
                    maxRows: 10,
                  }"
                />
              </n-form-item>
            </n-form>
          </n-space>
        </n-modal>
        <n-modal 
          v-model:show="editModalShow"
          title="编辑进展"
          preset="dialog"
          positive-text="提交"
          negative-text="取消"
          @positive-click="editSubmitCallback"
          @negative-click="editCancelCallback"
        >
          <n-space vertical style="margin-top: 20px; gap: 20px">
            <n-radio-group v-model:value="currentProgress.type">
              <n-space>
                <n-radio label="INFO" value="info" />
                <n-radio label="SUCCESS" value="success" />
                <n-radio label="WARNING" value="warning" />
                <n-radio label="ERROR" value="error" />
              </n-space>
            </n-radio-group>
            <div>
              <n-input-number 
                v-model:value="currentProgress.percentage" 
                size="small"
                :step="10"
              >
                <template #suffix>
                  %
                </template>
              </n-input-number>
            </div>
            <n-form ref="formRef" :model="currentProgress">
              <n-form-item path="content" label="进展描述">
                <n-input
                  v-model:value="currentProgress.content"
                  type="textarea"
                  :autosize="{
                    minRows: 3,
                    maxRows: 10,
                  }"
                />
              </n-form-item>
            </n-form>
          </n-space>
        </n-modal>
        <n-modal 
          v-model:show="deleteModalShow"
        >
          <n-dialog
            type="warning"
            title="删除进展"
            content="是否确认删除此进展？"
            negative-text="取消"
            positive-text="确认"
            @positive-click="deleteSubmitCallback"
            @negative-click="deleteCancelCallback"
            @close="deleteCancelCallback"
          />
        </n-modal>
      </div>
    </div>
  </div>
  <div class="hovered-card" style="margin-top: 10px;">
    <n-upload
      abstract
      v-model:file-list="fileList.progress"
      show-download-button
      @change="(data) => handleUploadChange('progress', data)"
      @remove="(data) => handleRemove(props.requireItem.id, 'progress', data)"
      @download="(file) => handleDownload(props.requireItem.id, 'progress', file)"
      :custom-request="(obj) => attachmentUploadRequest(props.requireItem.id, 'progress', obj)"
    >
      <div class="upload-header">
        <span style="color: grey">附件</span>
        <n-space>
          <n-button 
            v-if="currentLockStatus"
            text 
            @click="handleLockClick(props.requireItem.id, 'progress', false)"
          >
            <n-tooltip>
              <template #trigger>
                <n-icon :size="22">
                  <IosLock />
                </n-icon>
              </template>
              解除锁定
            </n-tooltip>
          </n-button>
          <n-button
            v-if="!currentLockStatus"
            text 
            @click="handleLockClick(props.requireItem.id, 'progress', true)"
          >
            <n-tooltip>
              <template #trigger>
                <n-icon :size="22" color="#cacaca">
                  <IosUnlock />
                </n-icon>
              </template>
              锁定附件
            </n-tooltip>
          </n-button>
          <n-upload-trigger v-if="!currentLockStatus" #="{ handleClick }" abstract>
            <n-button text @click="handleClick">
              <n-tooltip>
                <template #trigger>
                  <n-icon :size="24">
                    <DriveFolderUploadRound />
                  </n-icon>
                </template>
                上传附件
              </n-tooltip>
            </n-button>
          </n-upload-trigger>
        </n-space>
      </div>
      <n-upload-file-list />
    </n-upload>
  </div>
</template>

<script setup>
import { NTooltip, NAvatar, NIcon, NButton, useMessage } from 'naive-ui';
import { CheckCircle, Edit } from '@vicons/fa';
import { Delete24Regular as Delete } from '@vicons/fluent';
import { DriveFolderUploadRound } from '@vicons/material';
import { IosLock, IosUnlock } from '@vicons/ionicons4';
import { createDefaultColumns } from '../modules/table';
import { getRequireItem, getRequirePackage, getRequireProgress } from '@/api/get';
import { addRequireProgress, addRequirePackageTask } from '@/api/post';
import { deleteRequireProgress } from '@/api/delete';
import { updateRequireProgress, updateLockRequireAttachment } from '@/api/put';
import { 
  fileList,
  getFileList,
  handleRemove, 
  handleUploadChange, 
  attachmentUploadRequest,
  handleDownload,
  cleanAttachmentList
} from '../modules/attachment';
import Timeline from '@/components/timeline/timeline';
import TimelineItem from '@/components/timeline/timelineItem';
import MemberMenu from '../memberMenu/MemberMenu';
import UserAvatarGroup from '@/components/avatarGroup/UserAvatarGroup';

const props = defineProps({
  requireItem: {
    type: Object,
  }
});

const message = useMessage();

const item = ref(props.requireItem);
const progressRef = ref(null);
const requireProgress = ref([]);
const packageList = ref([]);
const currentLockStatus = ref(false);

function renderIcon(row, step) {
  if (row.targets?.includes(step)) {
    if (
      row.status === '已完成' || row.targets.indexOf(step) <= row.targets.indexOf(row.status)
    ) {
      return h(
        NIcon,
        {
          color: '#18A058',
          size: '18',
        },
        {
          default: () => h(CheckCircle),
        }
      );
    }
    return h(
      NIcon,
      {
        color: '#c0c0c0',
        size: '18',
      },
      {
        default: () => h(CheckCircle),
      }
    );
  }
  return null;
}

const columns = [
  ...createDefaultColumns(renderIcon),
  {
    key: 'executor',
    title: '责任人',
    render: (row) => {
      if (props.requireItem.acceptor) {
        if (!row.executor) {
          if (props.requireItem.acceptor?.type === 'person') {
            return h(
              NTooltip,
              {},
              {
                trigger: () => h(
                  NAvatar,
                  {
                    round: true,
                    size: 22,
                    src: props.requireItem.acceptor.avatar_url
                  }
                ),
                default: () => h(
                  'span',
                  {},
                  props.requireItem.acceptor.user_name
                ),
              }
            );
          }
          return h(
            MemberMenu,
            {
              type: 'PERSON',
              groupId: props.requireItem.acceptor.group_id,
              onChoose: (user) => {
                addRequirePackageTask(props.requireItem.id, row.id, { executor_id: user.id })
                  .then(() => {
                    message.success(`子任务已创建，责任人指定为${user.name}`);
                    getRequirePackage(props.requireItem.id)
                      .then((res) => {
                        packageList.value = res.data;
                      });
                  });
              },
            },
            {
              label: () => {
                if (!row.executor) {
                  return h('span', {}, '指定');
                }
                return h(
                  NTooltip,
                  {},
                  {
                    trigger: () => h(
                      NAvatar,
                      {
                        round: true,
                        size: 22,
                        src: row.executor.avatar_url
                      }
                    ),
                    default: () => h(
                      'span',
                      {},
                      row.executor.user_name
                    )
                  }
                );
              },
            }
          );
        }
        return h(
          NTooltip,
          {},
          {
            trigger: () => h(
              NAvatar,
              {
                round: true,
                size: 22,
                src: row.executor.avatar_url
              }
            ),
            default: () => h(
              'span',
              {},
              row.executor.user_name
            )
          }
        );
      }
      return '';
    },
  },
  {
    key: 'participants',
    title: '协助人',
    render: (row) => {
      return h(
        UserAvatarGroup,
        {
          size: 22,
          max: 3,
          data: row.participants,
        },
      );
    },
  },
];

const postModalShow = ref(false);
const editModalShow = ref(false);
const deleteModalShow = ref(false);
const currentProgress = ref({});
const formRef = ref(null);
const postModel = ref({
  type: 'info',
  percentage: 0,
  content: undefined,
});

function handleProgressEditClick(_item) {
  editModalShow.value = true;
  currentProgress.value = JSON.parse(JSON.stringify(_item));
}

function handleProgressDeleteClick(_item) {
  deleteModalShow.value = true;
  currentProgress.value = JSON.parse(JSON.stringify(_item));
}

function getData() {
  getRequireItem(props.requireItem.id)
    .then((res) => {
      item.value = res.data;
      currentLockStatus.value = res.data.filelist_locked.progress;
    });
}

function getProgress() {
  getRequireProgress(props.requireItem.id)
    .then((res) => {
      requireProgress.value = res.data;
      postModel.value.percentage = res.data[0] ? res.data[0].percentage : 0;
    });
}

function handleLockClick(id, _type, _locked) {
  updateLockRequireAttachment(id, { type: _type, locked: _locked })
    .then(() => {
      if (!_locked) {
        window.$message?.success('已解除锁定');
      } else {
        window.$message?.success('已锁定');
      }
      getData();
    });
}

function cleanData() {
  postModel.value = {
    type: 'info',
    percentage: 0,
    content: undefined,
  };
  currentProgress.value = {};
  packageList.value = [];
}

function postSubmitCallback() {
  addRequireProgress(props.requireItem.id, postModel.value)
    .then(() => {
      postModel.value = {
        type: 'info',
        percentage: 0,
        content: undefined,
      };
      getProgress();
    })
    .catch(() => {
      message.error('进展新增失败');
    });
}

function postCancelCallback() {
  postModel.value = {
    type: 'info',
    percentage: 0,
    content: undefined,
  };
}

function editSubmitCallback() {
  updateRequireProgress(
    props.requireItem.id, 
    currentProgress.value.id, 
    {
      type: currentProgress.value.type,
      percentage: currentProgress.value.percentage,
      content: currentProgress.value.content,
    },
  )
    .then(() => {
      currentProgress.value = {};
      getProgress();
    })
    .catch(() => {
      message.error('进展更新失败');
    });
}

function editCancelCallback() {
  currentProgress.value = {};
}

function deleteSubmitCallback() {
  deleteRequireProgress(props.requireItem.id, currentProgress.value.id)
    .then(() => {
      getProgress();
      message.success('进展删除成功');
    })
    .catch(() => {
      message.error('进展删除失败');
    })
    .finally(() => {
      currentProgress.value = {};
      deleteModalShow.value = false;
    });
}

function deleteCancelCallback() {
  currentProgress.value = {};
  deleteModalShow.value = false;
}

onMounted(() => {
  getData();
  getRequirePackage(props.requireItem.id)
    .then((res) => {
      packageList.value = res.data;
    });
  getProgress();
  getFileList(props.requireItem.id, 'progress');
});

onUnmounted(() => {
  cleanAttachmentList();
  cleanData();
});
</script>

<style scoped lang="less">
.root-container {
  display: flex;
  .body-container {
    width: 80%;
    margin-right: 10px;
    .summary-container {
     padding-bottom: 10px;
     .hovered-card {
       padding: 0 20px;
       .title {
       }
       .subtitle {
         display: flex;
         align-items: center;
         span {
           margin: 0 10px;
         }
       }
       .body {
         margin: 0;
         padding-bottom: 20px;
       }
     }
    }
  }
  .sider-container {
    width: 20%;
  }
}
.upload-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: grey;
  margin: 0 20px;
}
.hovered-card {
  box-shadow: 0 1px 2px -2px rgba(0, 0, 0, 0.08), 0 3px 6px 0 rgba(0, 0, 0, 0.06), 0 5px 12px 4px rgba(0, 0, 0, 0.04);
  .progress-container {
    height: 500px;
    overflow: scroll;
    .timeline-container {
      margin-top: 0;
      padding-left: 4px;
    }
  }
}
</style>
