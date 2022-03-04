<template>
  <n-spin :show="showLoading" stroke="rgba(0, 47, 167, 1)">
    <div>
      <div class="accountInfo-header">
        <n-avatar
          style="position: absolute; top: 50%; z-index: 999"
          circle
          :size="100"
          :src="state.userInfo.avatar_url"
        />
      </div>
      <div class="container">
        <h3 class="item-title">基本信息</h3>
        <div class="info-item">
          <n-grid :cols="12">
            <n-gi :span="1">
              <p>用户名</p>
            </n-gi>
            <n-gi :span="2">
              <p>{{ state.userInfo.gitee_name }}</p>
            </n-gi>
            <n-gi :span="9"> </n-gi>
          </n-grid>
        </div>
        <div class="info-item">
          <n-grid :cols="12">
            <n-gi :span="1">
              <p>手机号</p>
            </n-gi>
            <n-gi :span="2">
              <n-input v-model:value="phone" type="text" v-if="isEditPhone" />
              <p v-else>{{ state.userInfo.phone }}</p>
            </n-gi>
            <n-gi :span="9">
              <n-button
                class="info-operation-btn"
                @click="editUserPhone"
                text
                tag="span"
                type="primary"
              >
                {{ isEditPhone ? '保存' : '修改' }}</n-button
              >
              <n-button
                v-if="isEditPhone"
                class="info-operation-btn"
                @click="cancelEditPhone"
                text
                tag="span"
                type="primary"
              >
                取消</n-button
              >
            </n-gi>
          </n-grid>
        </div>
        <div class="info-item">
          <n-grid :cols="12">
            <n-gi :span="1">
              <p>邮箱</p>
            </n-gi>
            <n-gi :span="2">
              <p>{{ state.userInfo.cla_email }}</p>
            </n-gi>
            <n-gi :span="9"> </n-gi>
          </n-grid>
        </div>
        <n-divider />
        <div
          class="item-title"
          style="justify-content: space-between; display: flex"
        >
          <h3>我的组织</h3>
          <n-button type="primary" @click="handleAddOrg">
            <template #icon>
              <n-icon>
                <add />
              </n-icon>
            </template>
            添加组织
          </n-button>
        </div>
        <n-data-table
          remote
          :columns="orgColumns"
          :data="state.userInfo.orgs"
          :pagination="pagination"
        />
      </div>
    </div>
    <n-modal
      v-model:show="showAddModal"
      preset="dialog"
      title="Dialog"
      :showIcon="false"
    >
      <template #header>
        <div>添加组织</div>
      </template>
      <n-form-item
        label="组织"
        :rule="orgNameRule"
        label-placement="left"
        label-align="left"
        label-width="100"
      >
        <n-select v-model:value="addInfo.org" :options="orgList" />
      </n-form-item>
      <n-form-item
        label="cla邮箱"
        :rule="claEmailRule"
        label-placement="left"
        label-align="left"
        label-width="100"
      >
        <n-input v-model:value="addInfo.claEmail" style="margin: 5px 0" />
      </n-form-item>
      <template #action>
        <n-space style="width: 100%">
          <n-button
            @click="showAddModal = false"
            ghost
            size="large"
            type="error"
            >取消</n-button
          >
          <n-button @click="submitAddOrg" size="large" ghost type="primary"
            >确认</n-button
          >
        </n-space>
      </template>
    </n-modal>
  </n-spin>
</template>
<script>
import { Add } from '@vicons/ionicons5';
import { modules } from './modules/index.js';

export default {
  components: { Add },
  setup() {
    modules.init();

    document.addEventListener('reloadInfo', () => {
      modules.init();
    });
    return modules;
  },
};
</script>
<style lang="less" scoped>
.info-item {
  margin: 10px 0;
}
.accountInfo-header {
  height: 100px;
  width: 100%;
  text-align: center;
  background-color: rgba(155, 155, 155, 0.2);
  position: relative;
}

.container {
  padding: 10px 50px;
  margin-top: 10px;
}

.title {
  margin-bottom: 10px;
}

.item-title {
  margin: 5px 0;
}

.info-item {
  margin: 10px 0;
}

.info-operation-btn {
  margin: 0 5px;
}

.msg-box {
  height: 100%;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}
</style>
