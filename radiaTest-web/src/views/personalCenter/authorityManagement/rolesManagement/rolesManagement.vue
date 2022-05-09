<template>
  <div>
    <n-descriptions label-placement="left">
      <template #header>
        <div style="display: flex; justify-content: space-between">
          <breadcrumb :list="titles" :fontsize="20" />
          <n-button type="error" @click="deleteRole"> 删除 </n-button>
        </div>
      </template>
      <n-descriptions-item>
        <template #label>描述</template>
        {{ description }}
      </n-descriptions-item>
    </n-descriptions>
    <div class="tabel-title">
      <h4>规则列表</h4>
      <n-button type="primary" @click="relationRule">
        <template #icon>
          <n-icon>
            <settings />
          </n-icon>
        </template>
        规则设置
      </n-button>
    </div>
    <n-data-table
      :columns="ruleColumns"
      :data="ruleData"
      :pagination="rulePagination"
    />
    <div class="tabel-title">
      <h4>用户列表</h4>
    </div>
    <n-data-table :columns="columns" :data="data" :pagination="pagination" />
    <n-drawer v-model:show="showDrawer" :width="700" placement="right">
      <n-drawer-content title="成员列表">
        <n-thing>
          <template #avatar>
            <n-avatar :src="roleInfo.avatar_url"> </n-avatar>
          </template>
          <template #header> {{ roleInfo.gitee_name }} </template>
          <template #description>
            <p>手机号:{{ roleInfo.phone }}</p>
            <p>邮箱:{{ roleInfo.cla_email }}</p>
          </template>
        </n-thing>
        <n-data-table
          :columns="ruleColumns"
          :data="ruleData"
          :pagination="rulePagination"
        />
      </n-drawer-content>
    </n-drawer>
    <modal-card
      title="规则"
      ref="ruleModal"
      cancelText="关闭"
      :showConfirm="false"
    >
      <template #form>
        <n-input
          style="margin:5px 0;width:800px"
          round
          placeholder="请输入名称"
          v-model:value="ruleSearch"
          @change="filterRules"
        >
          <template #suffix>
            <n-icon :component="Search" />
          </template>
        </n-input>
        <n-data-table
          :columns="relationRuleColumns"
          :data="relationRuleData"
          :pagination="relationRulePagination"
        />
      </template>
    </modal-card>
  </div>
</template>
<script>
import { modules } from './modules';
import breadcrumb from '@/components/breadcrumb/breadcrumb.vue';
// import { UserAddOutlined } from '@vicons/antd';
import { Search } from '@vicons/ionicons5';
import { Settings } from '@vicons/carbon';
import modalCard from '@/components/CRUD/ModalCard.vue';

export default {
  components: {
    breadcrumb,
    Settings,
    modalCard,
  },
  setup() {
    modules.getRoleInfo();
    return { ...modules, Search };
  },
};
</script>
<style lang="less" scoped>
.tabel-title {
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
}
</style>
