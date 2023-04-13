<template>
  <div class="designTemplate">
    <div class="designTemplate-left">
      <n-button style="width: 100%" type="success" dashed @click="createTemplateBtn"> 新建模板 </n-button>
      <n-input clearable type="text" v-model:value="searchWords" @change="getStrategyTemplateFn">
        <template #prefix>
          <n-icon color="#666666" :component="Search" />
        </template>
      </n-input>
      <div
        v-for="(item, index) in templateList"
        :key="index"
        :class="[{ active: checkedItem?.id === item.id }, 'templateItem']"
        @click.capture="handleTemplateClick(item)"
      >
        <div class="prefix">
          <n-icon size="20">
            <DocumentSharp />
          </n-icon>
          <span> {{ item.title }} </span>
        </div>
        <div class="suffix">
          <n-space>
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button text @click.capture="showEditModalBtn">
                  <n-icon :size="14" :component="Edit" />
                </n-button>
              </template>
              编辑
            </n-tooltip>
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button text @click="showDeleteModalBtn">
                  <n-icon :size="14" :component="Close" />
                </n-button>
              </template>
              删除
            </n-tooltip>
          </n-space>
        </div>
      </div>
    </div>
    <div class="designTemplate-right" v-if="kityminderValue">
      <div class="top">
        <div class="txts">
          <n-icon size="16" color="#666666">
            <Cubes />
          </n-icon>
          {{ checkedItem?.title }}
        </div>
      </div>
      <vue-kityminder
        class="myKityminder"
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
    <div class="designTemplate-empty" v-else>
      <n-empty />
    </div>
    <n-modal v-model:show="showCreateUpdateModal" :mask-closable="false">
      <n-card
        :title="createTitle(isCreate ? '创建模板' : '编辑模板')"
        size="large"
        :bordered="false"
        :segmented="{
          content: true
        }"
        style="width: 500px"
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
            <n-form-item-gi :span="12" label="模板名" path="templateName">
              <n-input v-model:value="formValue.templateName" placeholder="请输入模板名" />
            </n-form-item-gi>
          </n-grid>
        </n-form>
        <n-space>
          <n-button size="medium" type="error" @click="onNegativeClick" ghost> 取消 </n-button>
          <n-button size="medium" type="primary" @click="onPositiveClick" ghost> 提交 </n-button>
        </n-space>
      </n-card>
    </n-modal>
    <n-modal
      v-model:show="showDeleteModal"
      type="warning"
      preset="dialog"
      :title="`删除：${checkedItem?.title}`"
      content="确认删除此模板吗?"
      positive-text="确认"
      negative-text="取消"
      @positive-click="submitDeleteCallback"
      @negative-click="cancelDeleteCallback"
    />
  </div>
</template>

<script setup>
import { Search } from '@vicons/tabler';
import { DocumentSharp, Close } from '@vicons/ionicons5';
import { Edit, Cubes } from '@vicons/fa';
import { createTitle } from '@/assets/utils/createTitle';
import { NIcon } from 'naive-ui';
import { getStrategyTemplate } from '@/api/get';
import { createStrategyTemplate } from '@/api/post';
import { updateStrategyTemplate } from '@/api/put';
import { deleteStrategyTemplate } from '@/api/delete';

const searchWords = ref(null);
const checkedItem = ref(null); // 当前选中策略模板
const templateList = ref([]);
const showCreateUpdateModal = ref(false);
const isCreate = ref(false);
const formRef = ref(null);
const formValue = ref({
  templateName: null
});
const formRules = ref({
  templateName: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入模板名'
  }
});

// 新建模板
const createTemplateBtn = () => {
  showCreateUpdateModal.value = true;
  isCreate.value = true;
};

// 取消新建/编辑模板
const onNegativeClick = () => {
  showCreateUpdateModal.value = false;
  formValue.value = {
    templateName: null
  };
};

// 确定新建/编辑模板
const onPositiveClick = () => {
  formRef.value?.validate((errors) => {
    if (!errors) {
      if (isCreate.value) {
        createStrategyTemplate({
          title: formValue.value.templateName,
          tree: { data: { text: formValue.value.templateName, id: 0 } }
        }).then(() => {
          window.$message?.success('创建模板成功');
          onNegativeClick();
          getStrategyTemplateFn();
        });
      } else {
        updateStrategyTemplate(checkedItem.value.id, {
          title: formValue.value.templateName,
          tree: checkedItem.value.tree
        }).then(() => {
          checkedItem.value.title = formValue.value.templateName;
          onNegativeClick();
          getStrategyTemplateFn();
        });
      }
    } else {
      console.log(errors);
    }
  });
};

// 点击模板
const handleTemplateClick = (item) => {
  checkedItem.value = item;
  kityminderValue.value = item.tree;
};

// 查询模板
const getStrategyTemplateFn = () => {
  getStrategyTemplate({ title: searchWords.value })
    .then((res) => {
      templateList.value = [];
      res?.data?.forEach((item) => {
        templateList.value.push({
          id: item.id,
          orgId: item.org_id,
          title: item.title,
          tree: JSON.parse(item.tree)
        });
      });
    })
    .catch(() => {
      templateList.value = [];
    });
};

// 编辑按钮
const showEditModalBtn = () => {
  showCreateUpdateModal.value = true;
  formValue.value.templateName = checkedItem.value.title;
  isCreate.value = false;
};

const showDeleteModal = ref(false);

// 删除按钮
const showDeleteModalBtn = () => {
  showDeleteModal.value = true;
};

// 确认删除
const submitDeleteCallback = () => {
  showDeleteModal.value = false;
  deleteStrategyTemplate(checkedItem.value.id).then(() => {
    cancelDeleteCallback();
    getStrategyTemplateFn();
  });
};

// 取消删除
const cancelDeleteCallback = () => {
  showDeleteModal.value = false;
};

const kityminderValue = ref(null);
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

// 新增/编辑/删除节点
const handleContentChange = (data) => {
  updateStrategyTemplate(checkedItem.value.id, {
    title: checkedItem.value.title,
    tree: data
  }).then(() => {
    getStrategyTemplateFn();
  });
};

onMounted(() => {
  getStrategyTemplateFn();
});
</script>

<style scoped lang="less">
.designTemplate {
  display: flex;
  border: 1px solid #eee;
  border-radius: 4px;
  justify-content: space-between;
  height: 100%;
  .designTemplate-left {
    width: 20%;
    padding: 20px;
    border-right: 1px solid #eee;
    .title {
      font-size: 16px;
      color: #000000;
    }
    .n-input {
      margin: 10px 0;
    }
  }
  .designTemplate-right {
    width: 80%;
    .top {
      height: 56px;
      width: calc(100% - 40px);
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: #000000;
      font-size: 14px;
      border-bottom: 1px solid #eee;
      padding-left: 20px;
      padding-right: 20px;
      .txts {
        display: flex;
        align-items: center;
        color: #666666;
        i {
          margin-right: 5px;
        }
      }
    }

    :deep(.myKityminder) {
      height: calc(100% - 57px);
    }
  }
}
.templateItem {
  padding: 0 8px;
  height: 40px;
  display: flex;
  align-items: center;
  font-size: 12px;
  color: #000;
  cursor: pointer;
  border-radius: 5px;
  margin-bottom: 10px;
  justify-content: space-between;
  &:hover,
  &.active {
    background-color: #d2daf5;
  }
  .prefix {
    display: flex;
    align-items: center;
    .n-icon {
      color: #666666;
      margin-right: 5px;
    }
    span {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
  .suffix {
    display: none;
  }
  &:hover {
    .suffix {
      display: block;
    }
  }
}
.designTemplate-empty {
  width: 80%;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
