<template>
  <div class="header-wrap">
    <div class="strategy-title">{{ currentFeature?.label }}</div>
    <div v-if="currentFeature">
      <n-space>
        <n-button text @click="handleDeleteBtn" :disabled="!hasStrategy"
          ><n-icon size="16"><Delete24Regular /></n-icon>删除</n-button
        >
        <n-button text @click="handleStagingBtn" :disabled="currentFeature.status === 'submitted' || !hasStrategy"
          ><n-icon size="16"><SaveOutline /></n-icon>暂存</n-button
        >
        <n-button text @click="handleRestoreBtn" :disabled="currentFeature.status === 'submitted' || !hasStrategy"
          ><n-icon size="16"><ArrowBackCircleOutline /></n-icon>还原</n-button
        >
        <n-button text @click="handleSubmitBtn" :disabled="currentFeature.status === 'submitted' || !hasStrategy"
          ><n-icon size="16"><GitBranchOutline /></n-icon>提交</n-button
        >
      </n-space>
    </div>
  </div>
  <div v-if="hasStrategy" class="content-wrap">
    <vue-kityminder
      ref="kityminderRef"
      theme="fresh-blue"
      template="right"
      :toolbar-status="toolbar"
      :value="kityminderValue"
      @content-change="handleContentChange"
      @node-change="handleNodeChange"
      @selection-change="handleSelectionChange"
      @node-remove="handleNodeRemove"
      @contextmenu="handleContextMenu"
    ></vue-kityminder>
  </div>
  <div v-else class="content-wrap">
    <n-empty size="large">
      <template #icon>
        <n-icon>
          <Email />
        </n-icon>
      </template>
      <template #extra v-if="currentFeature">
        <n-space :size="50">
          <n-button size="large" round @click="handleApplyTemplate"> 应用模板 </n-button>
          <n-button size="large" round @click="handleCreateStrategy"> 创建策略 </n-button>
        </n-space>
      </template>
    </n-empty>
  </div>
  <ApplyTemplateModal
    :currentFeature="currentFeature"
    @applyTemplateCb="applyTemplateCb"
    ref="ApplyTemplateModalRef"
  ></ApplyTemplateModal>
  <n-modal v-model:show="showSubmitPullRequestModal" :mask-closable="false">
    <n-card
      :title="createTitle('提交PR')"
      size="large"
      :bordered="false"
      :segmented="{
        content: true
      }"
      style="width: 1000px"
    >
      <n-form
        label-placement="left"
        :label-width="80"
        :model="submitPullRequestFormValue"
        :rules="submitPullRequestFormRules"
        size="medium"
        ref="submitPullRequestFormRef"
      >
        <n-grid :cols="12">
          <n-form-item-gi :span="12" label="标题" path="title">
            <n-input v-model:value="submitPullRequestFormValue.title" placeholder="请输入标题" />
          </n-form-item-gi>
          <n-form-item-gi :span="12" label="描述" path="description">
            <Editor v-model="submitPullRequestFormValue.description" tag-name="div" :init="editorInit" />
          </n-form-item-gi>
        </n-grid>
      </n-form>
      <n-space>
        <n-button size="medium" type="error" @click="cancelSubmitPullRequest" ghost> 取消 </n-button>
        <n-button size="medium" type="primary" @click="submitPullRequestBtn" ghost> 提交 </n-button>
      </n-space>
    </n-card>
  </n-modal>
</template>

<script setup>
import { ArrowBackCircleOutline, SaveOutline, GitBranchOutline } from '@vicons/ionicons5';
import { Email } from '@vicons/carbon';
import { Delete24Regular } from '@vicons/fluent';
import ApplyTemplateModal from './ApplyTemplateModal.vue';
import { createTitle } from '@/assets/utils/createTitle';
import Editor from '@tinymce/tinymce-vue';
import { NIcon } from 'naive-ui';
import { getStrategy } from '@/api/get';
import { createStrategy, strategyCommitStage, strategySubmmit } from '@/api/post';
import { deleteStrategyCommit, deleteStrategy } from '@/api/delete';
import { storage } from '@/assets/utils/storageUtils';

const props = defineProps(['currentFeature']);
const { currentFeature } = toRefs(props);
const emits = defineEmits(['submitPullRequestCb']);
const hasStrategy = ref(false); // 是否有测试策略
const kityminderRef = ref(null);
const toolbar = ref({
  show: true, // 整个工具栏
  left: true, // 左侧工具栏
  right: true, // 右侧工具栏
  appendSiblingNode: true, // 插入同级
  appendChildNode: true, // 插入下级
  arrangeUp: true, // 上移
  arrangeDown: true, // 下移
  removeNode: true, // 删除
  text: true, // 文本框
  template: false, // 模板
  theme: false, // 主题
  hand: true, // 模式
  resetLayout: true, // 整理布局
  zoomOut: true, // 缩小
  zoomIn: true // 放大
});
const kityminderValue = ref({});
const strategyId = ref(null); // 测试策略ID

// 新增/编辑/删除节点
const handleContentChange = (data) => {
  kityminderValue.value = data;
};

// 删除
const handleDeleteBtn = () => {
  deleteStrategy(currentFeature.value.info.product_feature_id, {
    org_id: currentFeature.value.info.org_id,
    gitee_id: storage.getValue('gitee_id')
  }).then(() => {
    hasStrategy.value = false;
    kityminderValue.value = {};
    strategyId.value = null;
  });
};

// 还原
const handleRestoreBtn = () => {
  deleteStrategyCommit(strategyId.value).then(() => {
    getStrategyFn();
  });
};

// 暂存
const handleStagingBtn = () => {
  strategyCommitStage(strategyId.value, { commit_tree: kityminderValue.value }).then(() => {
    window.$message?.success('暂存成功！');
  });
};

// 提交
const handleSubmitBtn = () => {
  showSubmitPullRequestModal.value = true;
};

// 应用模板
const handleApplyTemplate = () => {
  ApplyTemplateModalRef.value.showModal = true;
};

// 应用模板回调
const applyTemplateCb = () => {
  getStrategyFn();
};

// 创建策略
const handleCreateStrategy = () => {
  createStrategy(currentFeature.value.info.product_feature_id, {
    tree: {
      data: { text: currentFeature.value.label, id: 0 }
    }
  }).then(() => {
    getStrategyFn();
  });
};

// 查询测试策略
const getStrategyFn = () => {
  getStrategy(currentFeature.value.info.product_feature_id)
    .then((res) => {
      hasStrategy.value = true;
      if (res.data?.commit_tree) {
        kityminderValue.value = JSON.parse(res.data.commit_tree) || {};
        strategyId.value = res.data.strategy_id;
      } else {
        kityminderValue.value = JSON.parse(res.data.tree) || {};
        strategyId.value = res.data.id;
      }
    })
    .catch(() => {
      hasStrategy.value = false;
      kityminderValue.value = {};
      strategyId.value = null;
    });
};

const ApplyTemplateModalRef = ref(null);

const showSubmitPullRequestModal = ref(false); // 显示提交PR弹框
const submitPullRequestFormRef = ref(null);
const submitPullRequestFormValue = ref({
  title: '',
  description: ''
});
const submitPullRequestFormRules = ref({
  title: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入标题'
  }
});
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
  plugins: 'image imagetools nonbreaking',
  toolbar:
    'undo redo fontsizeselect fontselect|underline forecolor backcolor bold italic strikethrough image subscript superscript removeformat|',
  content_style: 'p {margin: 5px 0; font-size: 14px}',
  fontsize_formats: '12px 14px 16px 18px 24px 36px 48px 56px 72px',
  font_formats:
    '微软雅黑=Microsoft YaHei,Helvetica Neue,PingFang SC,sans-serif;苹果苹方=PingFang SC,Microsoft YaHei,sans-serif;宋体=simsun,serif;仿宋体=FangSong,serif;黑体=SimHei,sans-serif;Arial=arial,helvetica,sans-serif;Arial Black=arial black,avant garde;Book Antiqua=book antiqua,palatino;',
  branding: false, // 隐藏右下角技术支持
  elementpath: false, // 隐藏底栏的元素路径
  nonbreaking_force_tab: true,
  resize: false, // 禁止改变大小
  statusbar: false, // 隐藏底部状态栏
  // 图片上传
  images_upload_handler(blobInfo, success) {
    let reader = new FileReader();
    reader.readAsDataURL(blobInfo.blob());
    reader.onload = function () {
      success(this.result);
    };
  }
};

// 取消提交PR
const cancelSubmitPullRequest = () => {
  showSubmitPullRequestModal.value = false;
  submitPullRequestFormValue.value = {
    title: '',
    description: ''
  };
};

// 提交PR
const submitPullRequestBtn = (e) => {
  e.preventDefault();
  submitPullRequestFormRef.value?.validate((errors) => {
    if (!errors) {
      strategySubmmit(strategyId.value, {
        title: submitPullRequestFormValue.value.title,
        body: submitPullRequestFormValue.value.description
      }).then(() => {
        window.$message?.success('提交成功！');
        currentFeature.value.status = 'submitted';
        emits('submitPullRequestCb');
        cancelSubmitPullRequest();
      });
    } else {
      console.log(errors);
    }
  });
};

watch(currentFeature, () => {
  getStrategyFn();
});

onMounted(() => {
  getStrategyFn();
});
</script>

<style scoped lang="less">
.header-wrap {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  height: 50px;
  box-sizing: border-box;
  border-bottom: 1px solid rgb(239, 239, 245);

  .strategy-title {
    font-size: 30px;
  }
}

.content-wrap {
  height: calc(100% - 50px);
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
