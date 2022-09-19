<template>
  <n-spin :show="showLoading" stroke="rgba(0, 47, 167, 1)">
    <card-page title="配置管理">
      <n-tabs type="line" animated>
        <n-tab-pane name="checkItem" tab="检查项">
          <div class="btn-header">
            <n-button type="primary" @click="addCheckItemBtn">
              <template #icon>
                <n-icon>
                  <add />
                </n-icon>
              </template>
              新增检查项
            </n-button>
          </div>
          <n-divider />
          <h3>检查项</h3>
          <n-data-table
            remote
            :loading="checkItenTableLoading"
            :columns="checkItemColumns"
            :data="checkItemData"
            :pagination="checkItemPagination"
            @update:page="checkItemTablePageChange"
            @update:page-size="checkItemTablePageSizeChange"
          />
          <n-modal
            v-model:show="showAddCheckItemModal"
            preset="dialog"
            :on-close="closeAddCheckItemModal"
            :onMaskClick="closeAddCheckItemModal"
            :closeOnEsc="false"
            style="width: 700px"
          >
            <template #header>
              <h3>{{ isCreate ? '新增检查项' : '更改检查项' }}</h3>
            </template>
            <n-form
              ref="checkItemFormRef"
              :label-width="150"
              label-align="right"
              label-placement="left"
              :model="checkItemModel"
              :rules="checkItemFormRules"
            >
              <n-form-item label="字段名" path="field_name">
                <n-input v-model:value="checkItemModel.field_name" placeholder="请输入字段名"></n-input>
              </n-form-item>
              <n-form-item label="检查项名称" path="title">
                <n-input v-model:value="checkItemModel.title" placeholder="请输入检查项名称"></n-input>
              </n-form-item>
            </n-form>
            <template #action>
              <n-space style="width: 100%">
                <n-button type="error" size="large" ghost @click="closeAddCheckItemModal"> 取消 </n-button>
                <n-button size="large" type="primary" ghost @click="submitCheckItemInfo"> 提交 </n-button>
              </n-space>
            </template>
          </n-modal>
        </n-tab-pane>
      </n-tabs>
    </card-page>
  </n-spin>
</template>

<script setup>
import { showLoading } from '@/assets/utils/loading';
import { NButton, NIcon, NSpace } from 'naive-ui';
import { Add } from '@vicons/ionicons5';
import { useTable } from '@/hooks/useTable';
import textDialog from '@/assets/utils/dialog';
import { addCheckItem } from '@/api/post';
import { updateCheckItem } from '@/api/put';
import { deleteCheckItem } from '@/api/delete';

const checkItenTableLoading = ref(false);
const showAddCheckItemModal = ref(false);
const isCreate = ref(true);
const checkItemId = ref(null);
const checkItemModel = ref({
  field_name: '',
  title: ''
});
const checkItemData = ref([]);
const checkItemPagination = ref({
  page: 1,
  pageSize: 10, //受控模式下的分页大小
  pageCount: 1, //总页数
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
});
const getDataParams = ref({
  page_num: toRef(checkItemPagination.value, 'page'),
  page_size: toRef(checkItemPagination.value, 'pageSize')
});

const checkItemColumns = ref([
  {
    key: 'field_name',
    title: '字段名',
    align: 'center'
  },
  {
    key: 'title',
    title: '检查项名称',
    align: 'center'
  },
  {
    title: '操作',
    align: 'center',
    render(row) {
      return h(
        NSpace,
        {
          style: 'justify-content: center'
        },
        {
          default: () => {
            return [
              h(
                NButton,
                {
                  text: true,
                  onClick: () => {
                    isCreate.value = false;
                    checkItemModel.value = {
                      field_name: row.field_name,
                      title: row.title
                    };
                    checkItemId.value = row.id;
                    showAddCheckItemModal.value = true;
                  }
                },
                {
                  default: () => '编辑'
                }
              ),
              h(
                NButton,
                {
                  text: true,
                  onClick: () => {
                    textDialog('warning', '警告', '确认删除检查项？', async () => {
                      await deleteCheckItem(row.id);
                      checkItemPagination.value.page = 1;
                      useTable(
                        'v1/checkitem',
                        getDataParams.value,
                        checkItemData,
                        checkItemPagination,
                        checkItenTableLoading,
                        true
                      );
                    });
                  }
                },
                {
                  default: () => '删除'
                }
              )
            ];
          }
        }
      );
    }
  }
]);

const checkItemFormRules = ref({
  field_name: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入字段名'
  },
  title: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入检查项名称'
  }
});
const checkItemFormRef = ref(null);

const checkItemTablePageChange = (page) => {
  checkItemPagination.value.page = page;
};

const checkItemTablePageSizeChange = (pageSize) => {
  checkItemPagination.value.pageSize = pageSize;
  checkItemPagination.value.page = 1;
};

const addCheckItemBtn = () => {
  isCreate.value = true;
  showAddCheckItemModal.value = true;
};

const closeAddCheckItemModal = () => {
  checkItemModel.value = { field_name: '', title: '' };
  showAddCheckItemModal.value = false;
};

const submitCheckItemInfo = () => {
  checkItemFormRef.value?.validate(async (errors) => {
    if (!errors) {
      if (isCreate.value) {
        await addCheckItem(checkItemModel.value);
      } else {
        await updateCheckItem(checkItemId.value, checkItemModel.value);
      }
      useTable('v1/checkitem', getDataParams.value, checkItemData, checkItemPagination, checkItenTableLoading, true);
      closeAddCheckItemModal();
    }
  });
};

useTable('v1/checkitem', getDataParams.value, checkItemData, checkItemPagination, checkItenTableLoading);
</script>

<style lang="less">
.btn-header {
  display: flex;
  justify-content: space-between;
}
</style>
