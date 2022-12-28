<template>
  <div class="document-container">
    <div class="leftPart">
      <n-button
        style="width: 100%;"
        size="small"
        type="success"
        dashed 
        @click="() => { showCreateModal = true }"
      >
        新增文档
      </n-button>
      <n-input clearable type="text" size="small" v-model:value="searchWords">
        <template #prefix>
          <n-icon color="666666" :component="Search" />
        </template>
      </n-input>
      <div 
        v-for="(txt, txtIndex) in documentList" 
        :key="txtIndex" 
        :class="[{active: checkedItem.id === txt.id}, 'item']"
        @click="handleClick(txt)"
      >
        <div class="prefix">
          <n-icon color="666666" size="20" :component="Document" />
          <span> {{ txt.title }} </span>
        </div>
        <div class="suffix">
          <n-space>
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button text @click="() => { showEditModal = true; }">
                  <n-icon :size="14" :component="Edit"/>
                </n-button>
              </template>
              编辑
            </n-tooltip>
            <n-tooltip trigger="hover">
              <template #trigger>
                <n-button text @click="() => { showDeleteModal = true; }">
                  <n-icon :size="14" :component="Close"/>
                </n-button>
              </template>
              删除
            </n-tooltip>
          </n-space>
        </div>
      </div>
    </div>
    <div v-if="checkedItem.url" class="rightPart">
      <iframe
        :src="checkedItem.url"
        frameborder="0"
        width="100%"
        height="100%"
      />
    </div>
    <div v-else class="emptyPart">
      <n-empty />
    </div>
  </div>
  <n-modal 
    v-model:show="showCreateModal"
    preset="card"
    style="width: 600px;"
    title="新建文档"
    :bordered="false"
  >
    <n-form 
      ref="createFormRef"
      :model="createForm"
      :rules="createRules"
    >
      <n-form-item label="标题" path="title">
        <n-input
          clearable
          v-model:value="createForm.title"
        />
      </n-form-item>
      <n-form-item label="链接" path="url">
        <n-input
          clearable
          v-model:value="createForm.url"
        />
      </n-form-item>
    </n-form>
    <n-space>
      <n-button type="error" @click="cancelCreateCallback" ghost>
        取消
      </n-button>
      <n-button type="primary" @click="submitCreateCallback" ghost>
        提交
      </n-button>
    </n-space>
  </n-modal>
  <n-modal 
    v-model:show="showEditModal"
    preset="card"
    style="width: 600px;"
    title="编辑文档"
    :bordered="false"
  >
    <n-form 
      ref="editFormRef"
      :model="editForm"
      :rules="editRules"
    >
      <n-form-item label="标题" path="title">
        <n-input
          clearable
          v-model:value="editForm.title"
        />
      </n-form-item>
      <n-form-item label="链接" path="url">
        <n-input
          clearable
          v-model:value="editForm.url"
        />
      </n-form-item>
    </n-form>
    <n-space>
      <n-button type="error" @click="cancelEditCallback" ghost>
        取消
      </n-button>
      <n-button type="primary" @click="submitEditCallback" ghost>
        提交
      </n-button>
    </n-space>
  </n-modal>
  <n-modal
    v-model:show="showDeleteModal"
    type="warning"
    preset="dialog"
    :title="`删除：${checkedItem.title}`"
    content="确认删除此文档吗?"
    positive-text="确认"
    negative-text="放弃"
    @positive-click="submitDeleteCallback"
    @negative-click="cancelDeleteCallback"
  />
</template>
<script setup>
import { useMessage } from 'naive-ui';
import { Document } from '@vicons/carbon';
import { Close } from '@vicons/ionicons5';
import { Edit } from '@vicons/fa';
import { Search } from '@vicons/tabler';
import { getSuiteDocuments } from '@/api/get';
import { addSuiteDocument } from '@/api/post';
import { updateSuiteDocument } from '@/api/put';
import { deleteSuiteDocument } from '@/api/delete';

const message = useMessage();
const router = useRoute();

const documentList = ref([]);
const checkedItem = ref({});
const searchWords = ref();
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showDeleteModal = ref(false);

const createForm = ref({
  title: undefined,
  url: undefined,
});
const editForm = ref({
  title: undefined,
  url: undefined,
});

function documentInit() {
  let params = {};
  if (searchWords.value) {
    params.title = searchWords.value;
  }
  getSuiteDocuments(window.atob(router.params.suiteId), params)
    .then(res => {
      documentList.value = res.data;
    });
}

onMounted(() => {
  documentInit();
});

function handleClick(txt) {
  checkedItem.value = txt;
  editForm.value.title = txt.title;
  editForm.value.url = txt.url;
}

function cancelCreateCallback() {
  showCreateModal.value = false;
}
function submitCreateCallback() {
  addSuiteDocument(window.atob(router.params.suiteId), {
    ...createForm.value,
    suite_id: parseInt(window.atob(router.params.suiteId)),
  })
    .then(() => {
      message.success('创建成功');
      createForm.value = {
        title: undefined,
        url: undefined,
      };
      showCreateModal.value = false;
    })
    .finally(() => {
      documentInit();
    });
}
function cancelEditCallback() {
  showEditModal.value = false;
}
function submitEditCallback() {
  updateSuiteDocument(checkedItem.value.id, editForm.value)
    .then(() => {
      message.success('修改成功');
      editForm.value = {
        title: undefined,
        url: undefined,
      };
      showEditModal.value = false;
    })
    .finally(() => {
      documentInit();
    });
}
function cancelDeleteCallback() {
  showDeleteModal.value = false;
}
function submitDeleteCallback() {
  deleteSuiteDocument(checkedItem.value.id)
    .then(() => {
      message.success('删除成功');
      showDeleteModal.value = false;
    })
    .finally(() => {
      documentInit();
    });
}

watch(searchWords, () => {
  documentInit();
});
</script>

<style lang="less" scoped>
.document-container{
  min-height: 700px;
  display: flex;
  justify-content: flex-start;
  .leftPart{
    width:20%;
    padding: 20px;
    border-right: 1px solid #eee;
    overflow: scroll;
    .n-input{
      margin: 10px 0;
    }
    .item{
      padding: 0 8px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      color:#000;
      cursor: pointer;
      border-radius: 5px;
      margin-bottom: 10px;
      &:hover,
      &.active{
        background-color: #d2daf5;
      }
      .prefix{
        display: flex;
        align-items: center;
        .n-icon{
          color: #666666;
          margin-right: 5px;
        }
        span{
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
      .suffix{
        display: none;
      }
      &:hover{
        .suffix{
          display: block;
        }
      }
    }
  }
  .rightPart{
    overflow: scroll;
    width: 100%;
  }
  .emptyPart{
    display: flex;
    width: 100%;
    align-items: center;
    justify-content: center;
  }
}
</style>
