<template>
  <div>
    <n-data-table 
      :columns="columns"
      :data="packageList"
    />
  </div>
  <div class="hovered-card" style="margin-top: 10px;">
    <n-upload
      abstract
      v-model:file-list="fileList.validation"
      show-download-button
      @change="(data) => handleUploadChange('validation', data)"
      @remove="(data) => handleRemove(props.requireItem.id, 'validation', data)"
      @download="(file) => handleDownload(props.requireItem.id, 'validation', file)"
      :custom-request="(obj) => attachmentUploadRequest(props.requireItem.id, 'validation', obj)"
    >
      <div class="upload-header">
        <span style="color: grey">交付件</span>
        <n-space>
          <n-button 
            v-if="currentLockStatus"
            text 
            @click="handleLockClick(props.requireItem.id, 'validation', false)"
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
            @click="handleLockClick(props.requireItem.id, 'validation', true)"
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
                上传交付件
              </n-tooltip>
            </n-button>
          </n-upload-trigger>
        </n-space>
      </div>
      <n-upload-file-list />
    </n-upload>
  </div>
  <n-modal 
    v-model:show="submitModalShow"
  >
    <n-dialog
      type="info"
      title="步骤验收"
      :content="`确认对步骤<${currentStep}>验收?`"
      negative-text="取消"
      positive-text="确认"
      @positive-click="validateSubmitCallback"
      @negative-click="validateCancelCallback"
      @close="validateCancelCallback"
    />
  </n-modal>
  <n-modal 
    v-model:show="withdrawModalShow"
  >
    <n-dialog
      type="warning"
      title="撤销验收"
      :content="`是否确认对步骤<${currentStep}>撤销验收?`"
      negative-text="取消"
      positive-text="确认"
      @positive-click="withdrawSubmitCallback"
      @negative-click="withdrawCancelCallback"
      @close="withdrawCancelCallback"
    />
  </n-modal>
</template>

<script setup>
import { NAvatar, NTooltip, NButton, NIcon, useMessage } from 'naive-ui';
import { CheckCircle } from '@vicons/fa';
import { IosLock, IosUnlock } from '@vicons/ionicons4';
import { DriveFolderUploadRound } from '@vicons/material';
import { createDefaultColumns } from '../modules/table';
import { getRequirePackage, getRequireItem } from '@/api/get';
import { 
  fileList,
  getFileList,
  handleRemove, 
  handleUploadChange, 
  attachmentUploadRequest,
  handleDownload,
  cleanAttachmentList
} from '../modules/attachment';
import { validateRequirePackage } from '@/api/post';
import MemberMenu from '../memberMenu/MemberMenu';
import { updateRequirePackageValidator, updateLockRequireAttachment } from '@/api/put';
import UserAvatarGroup from '@/components/avatarGroup/UserAvatarGroup';

const props = defineProps({
  requireItem: {
    type: Object,
    default: () => {},
  }
});

const message = useMessage();

const submitModalShow = ref(false);
const withdrawModalShow = ref(false);
const currentPackage = ref({});
const currentStep = ref(null);
const currentLockStatus = ref(false);

const packageList = ref([]);

function handleCheck(row, step, _type) {
  currentPackage.value = row;
  currentStep.value = step;
  if (_type === 'withdraw') {
    withdrawModalShow.value = true;
  } else if (_type === 'submit') {
    submitModalShow.value = true;
  }
} 

function renderIcon(row, step) {
  if (row.targets?.includes(step)) {
    if (row.completions?.includes(step)) {
      return h(
        NIcon,
        {
          class: 'check-button',
          color: '#18A058',
          size: '18',
          onClick: () => handleCheck(row, step, 'withdraw'),
        },
        {
          default: () => h(CheckCircle),
        }
      );
    }
    return h(
      NIcon,
      {
        class: 'check-button',
        color: '#c0c0c0',
        size: '18',
        onClick: () => handleCheck(row, step, 'submit'),
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
      if (row.executor) {
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
              row.executor.gitee_name
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
  {
    key: 'validator',
    title: '验收人',
    render: (row) => {
      if (props.requireItem.acceptor) {
        if (props.requireItem.publisher.type === 'person') {
          return h(
            NTooltip,
            {},
            {
              trigger: () => h(
                NAvatar,
                {
                  round: true,
                  size: 22,
                  src: props.requireItem.publisher.avatar_url
                }
              ),
              default: () => h(
                'span',
                {},
                props.requireItem.publisher.gitee_name
              ),
            }
          );
        }
        let _type = null;
        if (props.requireItem.publisher.type === 'organization') {
          _type = 'ORGANIZATION';
        } else {
          _type = 'PERSON';
        }
        return h(
          MemberMenu,
          {
            type: _type,
            groupId: props.requireItem.publisher.group_id,
            onChoose: (user) => {
              updateRequirePackageValidator(props.requireItem.id, row.id, user.id)
                .then(() => {
                  message.success(`验收人已指定为${user.name}`);
                  getRequirePackage(props.requireItem.id)
                    .then((res) => {
                      packageList.value = res.data;
                    });
                });
            },
          },
          {
            label: () => {
              if (!row.validator) {
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
                      src: row.validator.avatar_url
                    }
                  ),
                  default: () => h(
                    'span',
                    {},
                    row.validator.gitee_name
                  )
                }
              );
            },
          }
        );
      }
      return '';
    },
  },
];

function validateSubmitCallback() {
  let _completions = [];
  if (currentPackage.value.completions) {
    _completions = JSON.parse(JSON.stringify(currentPackage.value.completions));
  }
  _completions.push(currentStep.value);
  validateRequirePackage(props.requireItem.id, currentPackage.value.id, { completions: _completions })
    .then(() => {
      message.success(`已确认对步骤<${currentStep.value}>的验收`);
      getRequirePackage(props.requireItem.id)
        .then((res) => {
          packageList.value = res.data;
        });
    })
    .finally(() => {
      submitModalShow.value = false;
    });
}

function validateCancelCallback() {
  submitModalShow.value = false;
}

function withdrawSubmitCallback() {
  let _completions = [];
  if (currentPackage.value.completions) {
    _completions = JSON.parse(JSON.stringify(currentPackage.value.completions));
  }
  _completions.splice(_completions.indexOf(currentStep.value), 1);
  validateRequirePackage(props.requireItem.id, currentPackage.value.id, { completions: _completions })
    .then(() => {
      message.success(`已撤销对步骤<${currentStep.value}>的验收`);
      getRequirePackage(props.requireItem.id)
        .then((res) => {
          packageList.value = res.data;
        });
    })
    .finally(() => {
      withdrawModalShow.value = false;
    });
}

function withdrawCancelCallback() {
  withdrawModalShow.value = false;
}

function getData() {
  getRequireItem(props.requireItem.id)
    .then((res) => {
      currentLockStatus.value = res.data.filelist_locked.validation;
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

onMounted(() => {
  getData();
  getRequirePackage(props.requireItem.id)
    .then((res) => {
      packageList.value = res.data;
    });
  getFileList(props.requireItem.id, 'validation');
});

onUnmounted(() => {
  cleanAttachmentList();
  packageList.value = [];
});
</script>

<style scoped lang="less">
.header-container {
  display: flex;
  padding: 10px;
  .validate-progress {
    width: 15%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .timeline-progress {
    width: 85%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}
.upload-header {
  display: flex;
  justify-content: space-between;
  color: grey;
  margin: 0 20px;
}
.hovered-card {
  margin:10px 0;
  box-shadow: 0 1px 2px -2px rgba(0, 0, 0, 0.08), 0 3px 6px 0 rgba(0, 0, 0, 0.06), 0 5px 12px 4px rgba(0, 0, 0, 0.04)
}
:deep(.check-button:hover ){
  cursor: pointer;
}
</style>
