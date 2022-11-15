<template>
  <n-thing class="content-container">
    <template #description>
      <collapse-list :list="list" style="margin-top: 20px;" />
      <n-divider />
      <n-collapse default-expanded-names="pkgList">
        <n-collapse-item title="涉及软件包" name="pkgList">
          <n-data-table
            :columns="columns"
            :data="packageList"
          />
        </n-collapse-item>
      </n-collapse>
      <n-divider />
      <pre class="description">{{ item.description }}</pre>
    </template>
    <template #action>
      <n-upload
        abstract
        v-model:file-list="fileList.statement"
        show-download-button
        @change="(data) => handleUploadChange('statement', data)"
        @remove="(data) => handleRemove(props.requireItem.id, 'statement', data)"
        @download="(file) => handleDownload(props.requireItem.id, 'statement', file)"
        :custom-request="(obj) => attachmentUploadRequest(props.requireItem.id, 'statement', obj)"
      >
        <div class="upload-header">
          <span style="color: grey">附件</span>
          <n-space>
            <n-button 
              v-if="currentLockStatus"
              text 
              @click="handleLockClick(props.requireItem.id, 'statement', false)"
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
              @click="handleLockClick(props.requireItem.id, 'statement', true)"
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
    </template>
  </n-thing>
</template>

<script setup>
import { defineProps } from 'vue';
import { NIcon } from 'naive-ui';
import { CheckCircle } from '@vicons/fa';
import { IosLock, IosUnlock } from '@vicons/ionicons4';
import { createDefaultColumns } from '../modules/table';
import { DriveFolderUploadRound } from '@vicons/material';
import { getRequirePackage, getRequireItem } from '@/api/get';
import { 
  fileList,
  getFileList,
  handleRemove, 
  handleUploadChange, 
  attachmentUploadRequest,
  handleDownload,
  cleanAttachmentList,
} from '../modules/attachment';
import { updateLockRequireAttachment } from '@/api/put';

const props = defineProps({
  requireItem: {
    type: Object,
    default: () => {}
  },
});

const item = ref({});
const packageList = ref([]);
const currentLockStatus = ref(false);

function renderIcon(row, target) {
  if (row.targets.includes(target)) {
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
  return null;
}

const columns = createDefaultColumns(renderIcon);

function renderPublisherType (_type) {
  if (_type === 'person') {
    return '个人';
  } else if (_type === 'group') {
    return '团队';
  } else if (_type === 'organization') {
    return '组织';
  }
  return '未知类型';
}

const list = ref([
  {
    title: '基础信息',
    name: 'basicInfo',
    rows: [
      { 
        cols: [
          { label: '简介', value: props.requireItem.remark },
          { label: '预计工作量', value: `${props.requireItem.payload}人月` }
          { label: '项目周期', value: `${props.requireItem.period}天` }
        ] 
      },
      { 
        cols: [
          { 
            label: '发布人', 
            value: props.requireItem.publisher.name 
              ? props.requireItem.publisher.name 
              : props.requireItem.publisher.gitee_name
          },
          { label: '需求类型', value: renderPublisherType(props.requireItem.publisher.type) }
          { label: '发布时间', value: props.requireItem.create_time }
        ] 
      },
      { 
        cols: [
          { label: '影响力奖励', value: props.requireItem.total_reward }, 
          { label: '影响力门槛', value: props.requireItem.influence_require }, 
          { label: '信誉分门槛', value: props.requireItem.behavior_require }
        ] 
      },
    ],
  },
]);

function getData() {
  getRequireItem(props.requireItem.id)
    .then((res) => {
      item.value = res.data;
      currentLockStatus.value = res.data.filelist_locked.statement;
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
  getFileList(props.requireItem.id, 'statement');
});

onUnmounted(() => {
  cleanAttachmentList();
});
</script>

<style scoped>
:deep(.n-thing-avatar-header-wrapper) {
  display: block;
}
.description {
  white-space: pre-wrap;
  word-wrap: break-word;
}
.upload-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: grey;
  margin: 0 20px 0 0;
}
</style>
