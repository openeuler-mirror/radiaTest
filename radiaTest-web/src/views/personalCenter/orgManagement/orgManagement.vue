<template>
  <n-spin :show="showLoading" stroke="rgba(0, 47, 167, 1)">
    <card-page title="组织管理">
      <div class="btn-header">
        <n-button type="primary" @click="openRegisterOrgWindow">
          <template #icon>
            <n-icon>
              <add />
            </n-icon>
          </template>
          注册新组织
        </n-button>
      </div>
      <n-divider />
      <h3>组织</h3>
      <n-data-table
        :columns="orgColumns"
        :data="orgs"
        :pagination="pagination"
        :row-key="(row) => row.organization_id"
      />
      <n-modal
        v-model:show="showRegisterOrgWindow"
        preset="dialog"
        :on-close="closeOrgFrom"
        :onMaskClick="closeOrgFrom"
        :closeOnEsc="false"
        style="width: 700px"
      >
        <template #header>
          <h3>{{ isCreate ? '注册新组织' : '修改组织信息' }}</h3>
        </template>
        <n-form
          :label-width="150"
          label-align="left"
          require-mark-placement="left"
          label-placement="left"
          :model="registerModel"
          ref="regirsterRef"
          :rules="rules"
        >
          <n-form-item label="头像">
            <n-upload
              list-type="image-card"
              @update:file-list="uploadFinish"
              accept=".png,.jpg,.gif"
              :file-list="fileList"
            >
              点击上传
            </n-upload>
          </n-form-item>
          <n-form-item label="组织名称" path="name">
            <n-input v-model:value="registerModel.name" placeholder="请输入组织名"></n-input>
          </n-form-item>
          <n-form-item label="描述" path="description">
            <n-input v-model:value="registerModel.description" placeholder="请输入"></n-input>
          </n-form-item>
        </n-form>
        <template #action>
          <n-space style="width: 100%">
            <n-button type="error" size="large" ghost @click="closeOrgFrom"> 取消 </n-button>
            <n-button size="large" type="primary" ghost @click="submitOrgInfo"> 提交 </n-button>
          </n-space>
        </template>
      </n-modal>
    </card-page>
  </n-spin>
</template>

<script>
import { Add } from '@vicons/ionicons5';
import cardPage from '@/components/common/cardPage';
import { modules } from './modules/index.js';
export default {
  components: {
    cardPage,
    Add,
  },
  watch: {
    fileList: {
      handler(val) {
        this.$nextTick(() => {
          if (
            val.length === 1 &&
            document.querySelector('.n-upload-trigger.n-upload-trigger--image-card')
          ) {
            document.querySelector('.n-upload-trigger.n-upload-trigger--image-card').style.display =
              'none';
          } else {
            document.querySelector('.n-upload-trigger.n-upload-trigger--image-card').style.display =
              'block';
          }
        });
      },
      deep: true,
    },
  },
  setup() {
    modules.getData();
    return modules;
  },
};
</script>

<style>
.btn-header {
  display: flex;
  justify-content: space-between;
}
</style>
