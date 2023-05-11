<template>
  <div class="codehub">
    <div class="search">
      <n-button type="primary" @click="showRepoModal"> 注册代码仓 </n-button>
      <n-icon size="20" color="#666666" class="refreshIcon" @click="getCodeData"> <md-refresh /> </n-icon>
      <n-input type="text" size="small" v-model:value="keyword" placeholder="按仓库名称搜索">
        <template #prefix>
          <n-icon color="666666" :component="Search" />
        </template>
      </n-input>
    </div>
    <div class="table">
      <n-data-table
        :pagination="codePagination"
        :columns="codeColumns"
        :data="codeData"
        :row-key="(row) => row.id"
        :loading = "codeTableLoading"
        remote
      />
    </div>
  </div>
  <n-modal
    v-model:show="repoModal"
    preset="dialog"
    title="注册代码仓"
  >
    <n-form
      ref="repoRef1"
      label-placement="top"
      :model="repoForm"
      :rules="repoRules"
    >
      <n-form-item label="所属框架" path="framework_id">
        <n-select
          v-model:value="repoForm.framework_id"
          placeholder="请选择"
          :options="frameworkList"
        />
      </n-form-item>
      <n-form-item label="名称" path="name">
        <n-input
          v-model:value="repoForm.name"
          placeholder="请输入名称"
        />
      </n-form-item>
      <n-form-item label="代码仓地址" path="git_url">
        <n-input v-model:value="repoForm.git_url" placeholder="仓库地址" />
      </n-form-item>
      <n-form-item label="分支" path="branch">
        <n-input v-model:value="repoForm.branch" placeholder="分支"/>
      </n-form-item>
      <n-form-item label="是否允许同步" path="sync_rule">
        <n-switch v-model:value="repoForm.sync_rule">
          <template #checked> 是 </template>
          <template #unchecked> 否 </template>
        </n-switch>
      </n-form-item>
      <n-form-item label="是否已适配" path="is_adapt">
        <n-switch v-model:value="repoForm.is_adapt">
          <template #checked> 是 </template>
          <template #unchecked> 否 </template>
        </n-switch>
      </n-form-item>
    </n-form>
    <template #action>
      <n-space style="width: 100%">
        <n-button type="error" ghost size="large" @click="closeRepoForm">
          取消
        </n-button>
        <n-button size="large" @click="submitRepoForm" type="primary" ghost>
          提交
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup>
import { MdRefresh } from '@vicons/ionicons4';
import { Search } from '@vicons/ionicons5';
import { Refresh } from '@vicons/tabler';
import { storage } from '@/assets/utils/storageUtils';
import { setGroupRepo } from '@/api/post.js';
import { getScopedGitRepo, getFramework, getGitRepoSync } from '@/api/get.js';
import { unkonwnErrorMsg } from '@/assets/utils/description';
import { NButton, NIcon, useMessage } from 'naive-ui';

const props = defineProps({ type: String });
const router = useRoute();
const message = useMessage();

const codeTableLoading = ref(false);
const codePagination = ref(false);
const codeData = ref([]);
const keyword = ref('');

const codeColumns = [
  {
    title: '仓库名称',
    key: 'name'
  },
  {
    title: '所属框架',
    key: 'frameworkName'
  },
  {
    title: '代码仓地址',
    key: 'git_url'
  },
  {
    title: '分支',
    key: 'branch',
  },
  {
    title: '同步策略',
    key: 'syncRule',
    render: (row) => row.sync_rule?'自动':'手动',
  },
  {
    title: '解析适配',
    key: 'adaptive',
    render: (row) => row.adaptive?'是':'否',
  },
  {
    key: 'operation',
    render: (row) => {
      return h(
        NButton,
        {
          strong: true,
          secondary: true,
          type: 'info',
          // round: true,
          onClick: () => {
            getGitRepoSync(row.id)
              .then(() => {
               message.loading('开始同步'); 
              })
              .catch((err) => {
                if (err.data?.error_code === '60009') {
                  message.info(err.data.error_msg);
                } else {
                  message.error(err.data?.error_msg || unkonwnErrorMsg);
                }
              });
          },
        },
        {
          icon: () => h(NIcon, { component: Refresh }),
          default: () => '重新同步',
        }
      );
    },
  }
];

function getCodeData() {
  let params = { 
    name: keyword.value ? keyword.value : undefined,
    type: props.type,
  };
  if (props.type === 'org') {
    params.org_id = parseInt(window.atob(router.params.taskId));
  } else if (props.type === 'group') {
    params.group_id = parseInt(window.atob(router.params.taskId));
  }
  getScopedGitRepo(params)
    .then(res => {
      res.data?.map(item => {
        item.frameworkName = item.framework.name;
        item.syncRule = item.sync_rule ? '是' : '否';
        item.isAdapt = item.is_adapt ? '是' : '否';
      });
      codeData.value = res.data;
    });
}

const repoModal = ref(false);
const frameworkList = ref([]);
const repoRef1 = ref();


const repoRules = {
  name: {
    trigger: ['blur', 'input'],
    message: '名称必填',
    required: true,
  },
  git_url: {
    trigger: ['blur', 'input'],
    required: true,
    validator(rule, value) {
      if (!value) {
        return new Error('仓库地址必填');
      } else if (
        !/^http(s)?:\/\/[a-z0-9-]+(.[a-z0-9-]+)*(:[0-9]+)?(\/.*)?$/.test(value)
      ) {
        return new Error('仓库地址格式有误!');
      }
      return true;
    },
  },
  branch: {
    trigger: ['blur'],
    required: true,
    message: '分支不可为空',
  }
};

const repoForm = ref({
  framework_id: '',
  name: '',
  git_url: '',
  branch: 'master',
  sync_rule: false,
  is_adapt: false
});

function getFrameworkOptions() {
  getFramework()
    .then(res => {
      frameworkList.value = res.data?.map(
        item => ({ label: item.name, value: item.id })
      );
    });
}

function showRepoModal() {
  getFrameworkOptions();
  repoModal.value = true;
}

function clearRepoForm() {
  repoForm.value = {
    framework_id: '',
    name: '',
    git_url: '',
    branch: 'master',
    sync_rule: false,
    is_adapt: false
  };
}

function closeRepoForm() {
  clearRepoForm();
  repoModal.value = false;
}

function submitRepoForm() {
  repoRef1.value?.validate((errors) => {
    if (!errors) {
      let body = { 
        permission_type: props.type,
        creator_id: storage.getValue('user_id'),
        org_id: parseInt(storage.getValue('loginOrgId')),
      };
      if (props.type === 'group') {
        body.group_id = parseInt(window.atob(router.params.taskId));
      }
      setGroupRepo({
        ...repoForm.value,
        ...body,
      }).then(() => {
        closeRepoForm();
        getCodeData();
      });
    } else {
      window.$message?.error('填写信息有误,请检查!');
    }
  });
}

onMounted(() => {
  getCodeData();
});
watch(keyword, () => { getCodeData(); });
</script>

<style lang="less" scoped>
.codehub{
  padding:20px;
  border:1px solid #eee;
  border-radius: 4px;
  margin-top:20px;
  .title{
    color: #000000;
    font-size: 16px;
    margin-bottom: 10px;
  }
  .search{
    overflow: hidden;
    margin-bottom: 15px;
    .n-button{
      float: left;
    }
    .n-input{
      float: right;
      width:200px;
      margin-right: 10px;
      margin-top:3px;
    }
    .n-icon.refreshIcon{
      float: right;
      margin-top:6px;
      cursor: pointer;
    }
  }
}
</style>
