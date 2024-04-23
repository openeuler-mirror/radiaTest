<template>
  <n-modal
    v-model:show="showModal"
    :mask-closable="false"
    @after-enter="enterModal"
    @after-leave="leaveModal"
  >
    <n-card
      :title="createTitle('新建Issue')"
      size="large"
      :bordered="false"
      :segmented="{
        content: true,
      }"
      style="width: 1000px"
    >
      <n-form
        label-placement="left"
        :label-width="80"
        :model="formValue"
        :rules="formRules"
        size="medium"
        ref="formRef"
      >
        <n-grid :cols="12">
          <n-form-item-gi :span="8" label="标题" path="title">
            <n-input v-model:value="formValue.title" placeholder="请输入标题" />
          </n-form-item-gi>
          <n-form-item-gi :span="4" label="优先级" path="priority">
            <n-select
              v-model:value="formValue.priority"
              placeholder="请选择优先级"
              :options="priorityOptions"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="8" label="代码仓" path="project_name">
            <n-auto-complete
              v-model:value="formValue.project_name"
              :options="projectNameOptions"
              placeholder="请输入代码仓"
              clearable
              :input-props="{
                autocomplete: 'disabled',
              }"
              :get-show="getShow"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="4" label="类型" path="issue_type_id">
            <n-select
              v-model:value="formValue.issue_type_id"
              placeholder="请选择类型"
              :options="issueTypeOptions"
              clearable
            />
          </n-form-item-gi>
          <n-form-item-gi :span="12" label="描述" path="description">
            <Editor v-model="formValue.description" tag-name="div" :init="editorInit" />
          </n-form-item-gi>
        </n-grid>
      </n-form>
      <n-space>
        <n-button size="medium" type="error" @click="onNegativeClick" ghost> 取消 </n-button>
        <n-button size="medium" type="primary" @click="onPositiveClick" ghost> 提交 </n-button>
      </n-space>
    </n-card>
  </n-modal>
</template>

<script setup>
import { createTitle } from '@/assets/utils/createTitle';
import Editor from '@tinymce/tinymce-vue';
import tinymce from 'tinymce/tinymce';
import { getIssueType, getGiteeProject } from '@/api/get';
import { createIssues } from '@/api/post';
const props = defineProps(['caseIssueModalData', 'taskDetailData']);
const { caseIssueModalData, taskDetailData } = toRefs(props);

const showModal = ref(false);
const formRef = ref(null);
const formValue = ref({
  title: null,
  priority: 0,
  description: null,
  issue_type_id: null,
  project_name: null,
});
const formRules = ref({
  title: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入标题',
  },
  description: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入描述',
  },
  issue_type_id: {
    required: true,
    type: 'number',
    trigger: ['blur', 'select'],
    message: '请选择类型',
  },
});
const priorityOptions = ref([
  { label: '不指定', value: 0 },
  { label: '严重', value: 4 },
  { label: '主要', value: 3 },
  { label: '次要', value: 2 },
  { label: '可选', value: 1 },
]);
const issueTypeOptions = ref([]);
const projectNameOptions = ref([]);

// 富文本配置
const editorInit = {
  language_url: require('@/assets/tinymce/zh_CN.js'), // 中文语言包路径
  language: 'zh_CN',
  skin_url: '/tinymce/skins/ui/oxide', // 编辑器皮肤样式
  content_css: '/tinymce/skins/content/default/content.min.css',
  menubar: false, // 隐藏菜单栏
  height: 400,
  width: '100%',
  toolbar_mode: 'scrolling', // 工具栏模式
  plugins: 'image  nonbreaking',
  toolbar:
    'undo redo fontsizeselect fontselect|underline forecolor backcolor bold italic strikethrough image subscript superscript removeformat|',
  content_style: 'p {margin: 5px 0; font-size: 14px}',
  fontsize_formats: '12px 14px 16px 18px 24px 36px 48px 56px 72px',
  font_formats:
    '微软雅黑=Microsoft YaHei,Helvetica Neue,PingFang SC,sans-serif;苹果苹方=PingFang SC,Microsoft YaHei,sans-serif;宋体=simsun,serif;仿宋体=FangSong,serif;黑体=SimHei,sans-serif;Arial=arial,helvetica,sans-serif;Arial Black=arial black,avant garde;Book Antiqua=book antiqua,palatino;',
  branding: false, // 隐藏右下角技术支持
  promotion: false,
  elementpath: false, // 隐藏底栏的元素路径
  nonbreaking_force_tab: true,
  resize: false, // 禁止改变大小
  statusbar: false, // 隐藏底部状态栏
  // 图片上传
  image_title: true,
  automatic_uploads: true,
  file_picker_types: 'image',
  file_picker_callback: (cb) => {
    const input = document.createElement('input');
    input.setAttribute('type', 'file');
    input.setAttribute('accept', 'image/*');

    input.addEventListener('change', (e) => {
      const file = e.target.files[0];

      const reader = new FileReader();
      reader.addEventListener('load', () => {
        const id = `blobid${new Date().getTime()}`;
        const blobCache = tinymce.activeEditor.editorUpload.blobCache;
        const base64 = reader.result.split(',')[1];
        const blobInfo = blobCache.create(id, file, base64);
        blobCache.add(blobInfo);

        cb(blobInfo.blobUri(), { title: file.name });
      });
      reader.readAsDataURL(file);
    });

    input.click();
  },
};

const onNegativeClick = () => {
  showModal.value = false;
};

const onPositiveClick = (e) => {
  e.preventDefault();
  formRef.value?.validate((errors) => {
    if (!errors) {
      createIssues({
        title: formValue.value.title,
        description: formValue.value.description,
        priority: formValue.value.priority,
        milestone_id: caseIssueModalData.value.milestoneId,
        case_id: caseIssueModalData.value.id,
        task_id: taskDetailData.value.detail.id,
        project_name: formValue.value.project_name,
        issue_type_id: formValue.value.issue_type_id,
      }).then(() => {
        onNegativeClick();
      });
    } else {
      console.log(errors);
    }
  });
};

const getIssueTypeOptions = () => {
  getIssueType().then((res) => {
    res?.data?.forEach((v) => {
      issueTypeOptions.value.push({
        label: v.title,
        value: v.id,
      });
    });
  });
};

const getGiteeProjectOptions = () => {
  getGiteeProject().then((res) => {
    res?.data?.forEach((v) => {
      projectNameOptions.value.push({
        label: v.name,
        value: v.name,
      });
    });
  });
};

// 代码仓提示选项始终存在
const getShow = () => {
  return true;
};

const enterModal = () => {
  getIssueTypeOptions();
  getGiteeProjectOptions();
};

const leaveModal = () => {
  formValue.value = {
    title: null,
    priority: 0,
    description: null,
    issue_type_id: null,
    project_name: null,
  };
};

defineExpose({
  showModal,
});
</script>

<style scoped lang="less"></style>
