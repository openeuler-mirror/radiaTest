<template>
  <div>
    <n-descriptions label-placement="left">
      <template #header>
        <div style="display: flex">
          <breadcrumb :list="titles" :fontsize="20" style="padding-right: 20px" />
          <n-button round quaternary type="error" @click="deleteRole">
            <n-icon :size="20">
              <delete />
            </n-icon>
          </n-button>
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
        权限变更
      </n-button>
    </div>
    <table-filter :filters="filters" @filterchange="filterChange" />
    <n-data-table :columns="ruleColumns" :data="ruleData" :pagination="rulePagination" />
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
          <template #header> {{ roleInfo.user_name }} </template>
        </n-thing>
        <n-data-table :columns="ruleColumns" :data="ruleData" :pagination="rulePagination" />
      </n-drawer-content>
    </n-drawer>
    <modal-card title="权限变更" ref="ruleModal" cancelText="关闭" :showConfirm="false">
      <template #form>
        <n-tabs animated v-model:value="tabValue" type="line" @update:value="getRelationRules">
          <n-tab-pane v-if="isPermitted" name="permitted" tab="授权权限域"></n-tab-pane>
          <n-tab-pane name="public" tab="公共权限域"></n-tab-pane>
        </n-tabs>
        <n-input-group>
          <n-input
            style="margin: 5px 0; width: 800px"
            round
            placeholder="搜索规则名称"
            v-model:value="aliasSearch"
            @change="relationRuleSearch"
          >
            <template #suffix>
              <n-icon :component="Search" />
            </template>
          </n-input>
          <n-input
            style="margin: 5px 0; width: 800px"
            round
            placeholder="搜索规则路由"
            v-model:value="uriSearch"
            @change="relationRuleSearch"
          >
            <template #suffix>
              <n-icon :component="Search" />
            </template>
          </n-input>
        </n-input-group>
        <n-data-table
          remote
          :columns="relationRuleColumns"
          :data="relationRuleData"
          :pagination="relationRulePagination"
          @update:page="relationRulePageChange"
          @update:page-size="relationRuleSizeChange"
          v-if="isAuthorized"
        />
        <n-empty v-else />
      </template>
    </modal-card>
  </div>
</template>
<script>
import { computed } from 'vue';
import { modules } from './modules';
import breadcrumb from '@/components/breadcrumb/breadcrumb.vue';
import { Search } from '@vicons/ionicons5';
import { Settings, Delete } from '@vicons/carbon';
import modalCard from '@/components/CRUD/ModalCard.vue';
import tableFilter from '@/components/filter/tableFilter.vue';
import { storage } from '@/assets/utils/storageUtils';

export default {
  components: {
    breadcrumb,
    Settings,
    Delete,
    modalCard,
    tableFilter,
  },
  setup() {
    modules.getRoleInfo();
    const isPermitted = computed(() => {
      if (storage.getValue('role') === 1) {
        modules.tabValue.value = 'public';
        return false;
      }
      return true;
    });
    return { ...modules, Search, isPermitted };
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
