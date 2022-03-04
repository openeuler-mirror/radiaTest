<template>
  <div>
    <n-spin :show="showLoading" stroke="rgba(0, 47, 167, 1)">
      <card-page title="成员管理">
        <n-layout has-sider>
          <n-layout-sider
            bordered
            content-style="padding: 24px;height:100%"
            :native-scrollbar="false"
          >
            <n-tree
              :data="roleMenu"
              :selected-keys="selectdRole"
              :expanded-keys="expandKeys"
              @update:expanded-keys="handleExpand"
              @update:selected-keys="selectKey"
            />
          </n-layout-sider>
          <n-layout-content
            content-style="padding: 24px;height:100%"
            :native-scrollbar="false"
          >
            <n-data-table
              remote
              :pagination="pagination"
              :columns="usersColumns"
              :data="usersData"
              :loading="loading"
              @update:page="handlePageChange"
            />
          </n-layout-content>
        </n-layout>
      </card-page>
    </n-spin>
  </div>
</template>
<script>
import { modules } from './modules';
import { showLoading } from '@/assets/utils/loading';
import cardPage from '@/components/common/cardPage';
export default {
  components: {
    cardPage
  },
  setup() {
    modules.getUserInfo();
    modules.getMenu();
    return {
      showLoading,
      ...modules
    };
  }
};
</script>
