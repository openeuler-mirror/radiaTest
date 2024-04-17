<template>
  <n-spin :show="showLoading" stroke="rgba(0, 47, 167, 1)">
    <card-page title="弱口令设置">
      <n-tabs type="line" animated>
        <n-tab-pane name="checkItem" tab="弱口令">
          <div class="btn-header">
            <n-button type="primary" @click="addCheckItemBtn">
              <template #icon>
                <n-icon>
                  <add />
                </n-icon>
              </template>
              新增弱口令
            </n-button>
          </div>
          <n-divider />
          <h3>弱口令字典</h3>
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
              <h3>{{ isCreate ? '新增弱口令' : '更改弱口令' }}</h3>
            </template>
            <n-form
              ref="checkItemFormRef"
              :label-width="150"
              label-align="right"
              label-placement="left"
              :model="checkItemModel"
              :rules="checkItemFormRules"
            >
              <n-form-item label="弱口令" path="rule">
                <n-input v-model:value="checkItemModel.rule" placeholder="请输入弱口令"></n-input>
              </n-form-item>
            </n-form>
            <template #action>
              <n-space style="width: 100%">
                <n-button type="error" size="large" ghost @click="closeAddCheckItemModal">
                  取消
                </n-button>
                <n-button size="large" type="primary" ghost @click="submitCheckItemInfo">
                  提交
                </n-button>
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
import { addWeakPwd } from '@/api/post';
import { updateWeakPwd } from '@/api/put';
import { deleteWeakPwd } from '@/api/delete';

const checkItenTableLoading = ref(false);
const showAddCheckItemModal = ref(false);
const isCreate = ref(true);
const weakPwdId = ref(null);
const checkItemModel = ref({
  rule: '',
});

const checkItemFormRules = ref({
  rule: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入弱口令',
  },
});
const checkItemFormRef = ref(null);
const checkItemData = ref([]);
const checkItemPagination = ref({
  page: 1,
  pageSize: 10, //受控模式下的分页大小
  pageCount: 1, //总页数
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50],
});
const getDataParams = ref({
  page_num: toRef(checkItemPagination.value, 'page'),
  page_size: toRef(checkItemPagination.value, 'pageSize'),
});

const checkItemColumns = ref([
  {
    key: 'rule',
    title: '口令',
    align: 'center',
  },
  {
    title: '操作',
    align: 'center',
    render(row) {
      return h(
        NSpace,
        {
          style: 'justify-content: center',
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
                      rule: row.rule,
                    };
                    weakPwdId.value = row.id;
                    showAddCheckItemModal.value = true;
                  },
                },
                {
                  default: () => '编辑',
                }
              ),
              h(
                NButton,
                {
                  text: true,
                  onClick: () => {
                    textDialog('warning', '警告', '确认删除检查项？', async () => {
                      await deleteWeakPwd(row.id);
                      checkItemPagination.value.page = 1;
                      useTable(
                        '/v1/admin/password-rule',
                        getDataParams.value,
                        checkItemData,
                        checkItemPagination,
                        checkItenTableLoading,
                        true
                      );
                    });
                  },
                },
                {
                  default: () => '删除',
                }
              ),
            ];
          },
        }
      );
    },
  },
]);

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
  checkItemModel.value = { rule: '' };
  showAddCheckItemModal.value = false;
};

const submitCheckItemInfo = () => {
  checkItemFormRef.value?.validate(async (errors) => {
    if (!errors) {
      if (isCreate.value) {
        await addWeakPwd(checkItemModel.value);
      } else {
        await updateWeakPwd(weakPwdId.value, checkItemModel.value);
      }
      useTable(
        '/v1/admin/password-rule',
        getDataParams.value,
        checkItemData,
        checkItemPagination,
        checkItenTableLoading,
        true
      );
      closeAddCheckItemModal();
    }
  });
};

useTable(
  '/v1/admin/password-rule',
  getDataParams.value,
  checkItemData,
  checkItemPagination,
  checkItenTableLoading
);
</script>

<style lang="less">
.btn-header {
  display: flex;
  justify-content: space-between;
}
</style>
