<template>
  <n-spin :show="showLoading" stroke="rgba(0, 47, 167, 1)" class="spin">
    <card-page title="权限管理" class="cardWrap">
      <n-layout has-sider content-style="height:100%;" class="layoutWrap">
        <n-layout-sider
          content-style="padding: 24px;height:100%;"
          width="400px"
          bordered
        >
          <div>
            <n-button type="primary" text @click="rulesView">
              <template #icon>
                <n-icon>
                  <PolicyOutlined />
                </n-icon>
              </template>
              规则
            </n-button>
          </div>
          <div class="leftHeader">
            <div class="searchWrap" style="width: 70%">
              <n-icon size="22" class="search"> <Search /> </n-icon>
              <n-input
                type="text"
                placeholder="输入关键字进行过滤"
                class="input"
              />
            </div>
            <n-button type="primary" @click="createRole">创建角色</n-button>
          </div>
          <n-list>
            <n-list-item>
              <n-thing title="角色列表">
                <n-tree
                  :data="roleList"
                  @update:selected-keys="selectRole"
                  :expanded-keys="expandRole"
                  :selected-keys="activeRole"
                  @update:expanded-keys="expandKey"
                />
              </n-thing>
            </n-list-item>
          </n-list>
        </n-layout-sider>
        <n-layout style="padding: 0 10px">
          <router-view :key="routerChange" />
        </n-layout>
      </n-layout>
      <role-form
        ref="roleCreateForm"
        type="create"
        @submitform="submitCreateFrom"
      />
    </card-page>
  </n-spin>
</template>

<script>
import { defineComponent } from 'vue';
import { modules } from './modules/index.js';
import cardPage from '@/components/common/cardPage';
import { Search } from '@vicons/tabler';
import { PolicyOutlined } from '@vicons/material';
import roleForm from '@/components/form/roleForm.vue';

export default defineComponent({
  components: {
    cardPage,
    Search,
    PolicyOutlined,
    roleForm,
  },
  computed: {
    routerChange() {
      return this.$route.path;
    }
  },
  setup() {
    modules.getRoleList();
    return {
      ...modules,
    };
  },
});
</script>

<style lang="less" scoped>
.n-layout-header,
.n-layout-footer {
  padding: 24px;
}

.leftHeader {
  display: flex;
  justify-content: space-between;
}

.searchWrap {
  position: relative;
  display: inline-flex;

  .search {
    position: absolute;
    top: 5px;
    right: 5px;
    z-index: 999;
  }

  .input {
    padding-right: 18px;
  }
}

.authorityTable {
  margin-top: 20px;
}

.spin {
  height: 100%;

  :deep(.n-spin-content) {
    height: 100%;
  }

  .cardWrap {
    height: 100%;

    .layoutWrap {
      height: 100%;
    }
  }
}
.role {
  margin-bottom: 10px;
}
.right {
  :deep(.n-descriptions-header) {
    font-weight: bold;
  }
}
</style>
