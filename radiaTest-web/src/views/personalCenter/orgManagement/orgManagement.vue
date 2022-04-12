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
        style="width: 700px"
      >
        <template #header>
          <h3>注册新组织</h3>
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
            >
              点击上传
            </n-upload>
          </n-form-item>
          <n-form-item label="组织名称" path="name">
            <n-input
              v-model:value="registerModel.name"
              placeholder="请输入组织名"
            ></n-input>
          </n-form-item>
          <n-form-item label="描述" path="description">
            <n-input
              v-model:value="registerModel.description"
              placeholder="请输入"
            ></n-input>
          </n-form-item>
          <n-form-item>
            <n-checkbox v-model:checked="requireCla" label="填写cla信息" />
          </n-form-item>
          <n-form-item
            v-if="requireCla"
            label="cla验证地址"
            path="claVerifyUrl"
          >
            <n-input
              v-model:value="registerModel.claVerifyUrl"
              placeholder="请输入cla验证地址"
            ></n-input>
          </n-form-item>
          <n-form-item v-if="requireCla" label="cla签署地址" path="claSignUrl">
            <n-input
              v-model:value="registerModel.claSignUrl"
              placeholder="请输入cla签署地址"
            ></n-input>
          </n-form-item>
          <n-form-item
            v-if="requireCla"
            label="cla验证通过的标志"
            path="claPassFlag"
          >
            <n-input
              v-model:value="registerModel.claPassFlag"
              placeholder="请输入cla验证通过的标志"
            ></n-input>
          </n-form-item>
          <n-form-item
            v-if="requireCla"
            label="请求方式"
            path="claRequestMethod"
          >
            <n-select
              v-model:value="registerModel.claRequestMethod"
              placeholder="请选择验证地址的请求方式"
              :options="requestOptions"
            ></n-select>
          </n-form-item>
          <n-form-item v-if="requireCla" label="url中的参数">
            <n-dynamic-input
              preset="pair"
              v-model:value="registerModel.urlParams"
              key-placeholder="键"
              value-placeholder="值"
            />
          </n-form-item>
          <n-form-item v-if="requireCla" label="body中的参数">
            <n-dynamic-input
              preset="pair"
              v-model:value="registerModel.bodyParams"
              key-placeholder="键"
              value-placeholder="值"
            />
          </n-form-item>
          <n-form-item>
            <n-checkbox
              v-model:checked="requireEnterprise"
              label="填写企业仓信息"
            />
          </n-form-item>
          <n-form-item
            v-if="requireEnterprise"
            label="enterprise"
            path="enterprise"
          >
            <n-input
              v-model:value="registerModel.enterprise"
              placeholder="请填写该组织码云企业仓ID"
              :maxlength="50"
            ></n-input>
          </n-form-item>
          <n-form-item
            v-if="requireEnterprise"
            label="oauth_client_id"
            path="oauth_client_id"
          >
            <n-input
              v-model:value="registerModel.oauth_client_id"
              placeholder="请填写oauth_client_id"
              :maxlength="50"
            ></n-input>
          </n-form-item>
          <n-form-item
            v-if="requireEnterprise"
            label="oauth_client_secret"
            path="oauth_client_secret"
          >
            <n-input
              v-model:value="registerModel.oauth_client_secret"
              placeholder="请填写oauth_client_secret"
              :maxlength="50"
            ></n-input>
          </n-form-item>
          <n-form-item
            v-if="requireEnterprise"
            label="oauth_scope"
            path="oauth_client_scope"
          >
            <n-dynamic-tags v-model:value="registerModel.oauth_client_scope" />
          </n-form-item>
        </n-form>
        <template #action>
          <n-space style="width: 100%">
            <n-button
              type="error"
              size="large"
              ghost
              @click="showRegisterOrgWindow = false"
            >
              取消
            </n-button>
            <n-button size="large" type="primary" ghost @click="submitOrgInfo">
              提交
            </n-button>
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
        if (val.length === 1) {
          document.querySelector(
            '.n-upload-trigger.n-upload-trigger--image-card'
          ).style.display = 'none';
        } else {
          document.querySelector(
            '.n-upload-trigger.n-upload-trigger--image-card'
          ).style.display = 'block';
        }
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
