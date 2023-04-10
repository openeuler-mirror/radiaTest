<template>
  <n-spin
    :show="showLoading"
    stroke="rgba(0, 47, 167, 1)"
  >
    <div>
      <div class="page-header">
        <n-button
          type="primary"
          @click="createGroup"
        >
          <template #icon>
            <n-icon>
              <add />
            </n-icon>
          </template>
          创建用户组
        </n-button>
        <div id="search">
          <n-input
            placeholder="请输入用户名组进行搜索"
            clearable
            v-model:value="searchGroupName"
          >
          </n-input>
          <n-button
            type="primary"
            @click="searchGroup"
          >搜索</n-button>
        </div>
      </div>
      <n-data-table
        remote
        :columns="columns"
        :data="state.dataList"
        :pagination="pagination"
        @update:page="turnPages"
        @update:page-size="turnPageSize"
        :row-props="groupRowProps"
      />
      <n-drawer
        :show="groupInfo.show"
        :width="800"
        placement="right"
        :on-update:show="drawerUpdateShow"
      >
        <n-drawer-content>
          <template #header>{{groupInfo.name}}</template>
          <n-data-table
            remote
            :columns="usersColumns"
            :data="groupInfo.usersData"
            :loading="tableLoading"
            :pagination="groupPagination"
            @update:page="groupTurnPages"
            @update:page-size="groupTurnPageSize"
          />
          <template #footer>
            <n-button
              type="primary"
              @click="addUser"
            >
              <template #icon>
                <n-icon>
                  <add />
                </n-icon>
              </template>
              添加用户
            </n-button>
          </template>
        </n-drawer-content>
      </n-drawer>
      <n-modal
        v-model:show="showCreateForm"
        preset="dialog"
        title="Dialog"
        :mask-closable="false"
        :showIcon="false"
      >
        <template #header>
          <div>创建用户组</div>
        </template>
        <n-form
          ref="formRef"
          :model="createModal"
          :rules="rules"
          label-placement="left"
          label-align="left"
          :label-width="100"
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
          <n-form-item
            label="用户组名"
            path="groupName"
          >
            <n-input
              placeholder="请输入用户组名"
              v-model:value="createModal.groupName"
            />
          </n-form-item>
          <n-form-item label="描述">
            <n-input
              placeholder="请输入组织描述"
              type="textarea"
              v-model:value="createModal.describe"
            />
          </n-form-item>
        </n-form>
        <template #action>
          <n-space style="width:100%">
            <n-button
              @click="onNegativeClick"
              type="error"
              size="large"
              ghost
            >取消</n-button>
            <n-button
              @click="onPositiveClick"
              type="primary"
              size="large"
              ghost
            >确认</n-button>
          </n-space>
        </template>
      </n-modal>
      <n-modal
        v-model:show="showAddUser"
        preset="dialog"
        title="Dialog"
        :showIcon="false"
        :mask-closable="false"
      >
        <template #header>
          <div>添加用户</div>
        </template>
        <div style="display: flex;">
          <n-input
            v-model:value="addUserInfo.name"
            placeholder="请输入用户名"
          ></n-input>
          <n-button
            type="primary"
            @click="searchUser"
          >添加</n-button>
        </div>
        <div style="height:200px;padding: 5px;overflow-y: auto;">
          <p style="font-size:14px;">已选用户:</p>
          <delete-item
            @deleteItem="deleteItems(index)"
            v-for="(item,index) in usersList"
            :key="index"
            style="text-align: center;width:80px;margin:3px;"
          >
            <n-avatar
              round
              size="small"
              :src="item.avatar_url"
            />
            <p style="max-width: 80px;">
              <n-ellipsis style="max-width: 80px;">
                {{item.user_name}}
              </n-ellipsis>
            </p>
          </delete-item>
        </div>
        <template #action>
          <n-space style="width:100%">
            <n-button
              type="error"
              ghost
              size="large"
              @click="cancelAdd"
            >
              取消
            </n-button>
            <n-button
              size="large"
              @click="handlePositiveClick"
              type="primary"
              ghost
            >
              提交
            </n-button>
          </n-space>
        </template>
      </n-modal>
    </div>
  </n-spin>
</template>

<script>
import deleteItem from '@/components/common/deleteItem.vue';
import { Add } from '@vicons/ionicons5';
import { modules } from './modules/index.js';

export default {
  components: {
    Add,
    deleteItem
  },
  name: 'userGroupManagement',
  setup () {
    modules.getDataList();
    modules.getGroupRole();
    return modules;
  },
  watch: {
    fileList: {
      handler (val) {
        if (val.length === 1) {
          document.querySelector('.n-upload-trigger.n-upload-trigger--image-card').style.display = 'none';
        } else {
          document.querySelector('.n-upload-trigger.n-upload-trigger--image-card').style.display = 'block';
        }
      },
      deep: true
    }
  },
  unmounted() {
    modules.allRole.value = {};
  },
};
</script>
<style lang="less" scope>
.page-header {
  display: flex;
  justify-content: space-between;
  margin: 5px 0;

  #search {
    width: 300px;
    display: flex;
  }
}
</style>
