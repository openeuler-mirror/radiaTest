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

          <n-form-item>
            <n-radio-group
              v-model:value="registerModel.authorityType"
              name="authorityTypeGroup"
              @update:value="changeAuthorityType"
            >
              <n-space>
                <n-radio value="gitee"> gitee鉴权 </n-radio>
                <n-radio value="oneid"> oneid鉴权 </n-radio>
              </n-space>
            </n-radio-group>
          </n-form-item>
          <n-form-item v-if="registerModel.authorityType === 'gitee'" style="margin-left: 25px">
            <n-radio-group
              v-model:value="registerModel.authoritySecondaryType"
              name="authoritySecondaryTypeGroup"
              @update:value="changeAuthoritySecondaryTypeGroup"
            >
              <n-space>
                <n-radio value="personal"> 个人应用 </n-radio>
                <n-radio value="enterprise"> 企业应用 </n-radio>
              </n-space>
            </n-radio-group>
          </n-form-item>
          <n-form-item label="oauth_login_url" path="oauthLoginUrl">
            <n-input
              v-model:value="registerModel.oauthLoginUrl"
              placeholder="请填写oauth_login_url"
            ></n-input>
          </n-form-item>
          <n-form-item label="oauth_client_id" path="oauthClientId">
            <n-input
              v-model:value="registerModel.oauthClientId"
              placeholder="请填写oauth_client_id"
            ></n-input>
          </n-form-item>
          <n-form-item label="oauth_client_secret" path="oauthClientSecret">
            <n-input
              v-model:value="registerModel.oauthClientSecret"
              placeholder="请填写oauth_client_secret"
            ></n-input>
          </n-form-item>
          <n-form-item label="oauth_scope" path="oauthClientScope">
            <n-dynamic-tags v-model:value="registerModel.oauthClientScope" />
          </n-form-item>
          <n-form-item label="oauth_get_token_url" path="oauthGetTokenUrl">
            <n-input
              v-model:value="registerModel.oauthGetTokenUrl"
              placeholder="请填写oauth_get_token_url"
            ></n-input>
          </n-form-item>
          <n-form-item label="oauth_get_user_info_url" path="oauthGetUserInfoUrl">
            <n-input
              v-model:value="registerModel.oauthGetUserInfoUrl"
              placeholder="请填写oauth_get_user_info_url"
            ></n-input>
          </n-form-item>
          <n-form-item
            label="gitee企业仓ID"
            path="enterpriseId"
            v-if="
              registerModel.authoritySecondaryType === 'enterprise' &&
              registerModel.authorityType === 'gitee'
            "
          >
            <n-input
              v-model:value="registerModel.enterpriseId"
              placeholder="请填写该组织gitee企业仓ID"
              :maxlength="50"
            ></n-input>
          </n-form-item>
          <n-form-item
            label="gitee企业仓令牌"
            path="enterpriseToken"
            v-if="
              registerModel.authoritySecondaryType === 'enterprise' &&
              registerModel.authorityType === 'gitee'
            "
          >
            <n-input
              v-model:value="registerModel.enterpriseToken"
              placeholder="请填写该组织gitee企业仓令牌"
            ></n-input>
          </n-form-item>
          <n-form-item
            label="gitee企业仓申请链接"
            path="enterpriseJoinUrl"
            v-if="
              registerModel.authoritySecondaryType === 'enterprise' &&
              registerModel.authorityType === 'gitee'
            "
          >
            <n-input
              v-model:value="registerModel.enterpriseJoinUrl"
              placeholder="若存在公开加入申请链接可填, URL必须存在协议头http或https"
            ></n-input>
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
