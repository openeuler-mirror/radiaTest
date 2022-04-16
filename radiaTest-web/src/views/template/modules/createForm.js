import { ref, watch } from 'vue';
import axios from '@/axios';
import {
  getProductOpts,
  getVersionOpts,
  getMilestoneOpts,
} from '@/assets/utils/getOpts.js';
import { storage } from '@/assets/utils/storageUtils';
import { currentOrg } from '@/components/header/profileMenu/modules/orgInfo';
import { createRepoOptions } from '@/assets/utils/getOpts';
import createAjax from '@/views/template/modules/createAjax.js';
import casesForm from '@/views/template/modules/casesForm.js';
import { getGroup } from '@/api/get';

const formRef = ref(null);
const formValue = ref({
  name: undefined,
  template_type: undefined,
  owner: undefined,
  product: undefined,
  version: undefined,
  milestone: undefined,
  description: undefined,
  git_repo: undefined,
});

const loading = ref(false);
const warning = ref(false);

const disabled = ref(false);

const ownerOpts = ref([]);
const productOpts = ref([]);
const versionOpts = ref([]);
const milestoneOpts = ref([]);
const typeOpts = ref([
  {
    label: '个人模板',
    value: 'personal',
  },
  {
    label: '团队模板',
    value: 'team',
  },
  {
    label: '组织模板',
    value: 'orgnization',
  },
]);

const getTeamOptions = () => {
  getGroup({ page_num: 1, page_size: 99999 })
    .then((res) => {
      ownerOpts.value = res.data.items.map((item) => {
        return {
          label: item.name,
          value: item.name,
        };
      });
    })
    .catch(() => {
      window.$message?.error(
        '无法获取所属团队信息，请检查网络或联系管理员处理'
      );
    });
};

watch(
  () => formValue.value.template_type,
  () => {
    if (formValue.value.template_type === 'personal') {
      disabled.value = true;
      formValue.value.owner = storage.getValue('gitee_name');
    } else if (formValue.value.template_type === 'team') {
      disabled.value = false;
      formValue.value.owner = null;
      getTeamOptions();
    } else if (formValue.value.template_type === 'orgnization') {
      disabled.value = true;
      formValue.value.owner = currentOrg.value;
    }
  }
);

const nameValidator = (rule, value) => {
  warning.value = false;
  if (!value) {
    return new Error('模板名不可为空');
  }
  loading.value = true;

  return axios.validate(
    '/v1/template',
    { name: formValue.value.name },
    loading,
    warning
  );
};

const rules = {
  name: {
    required: true,
    validator: nameValidator,
    trigger: ['blur'],
  },
  formwork_type: {
    required: true,
    message: '模板类型不可为空',
    trigger: ['blur'],
  },
  owner: {
    required: true,
    message: '权限归属/所有者 不可为空',
    trigger: ['blur'],
  },
  milestone: {
    required: true,
    message: '请绑定里程碑',
    trigger: ['blur'],
  },
};

const validateFormData = (context) => {
  formRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请检查输入合法性');
    } else {
      context.emit('valid');
    }
  });
};

const clean = () => {
  formValue.value = {
    name: undefined,
    template_type: undefined,
    owner: undefined,
    product: undefined,
    version: undefined,
    milestone: undefined,
    description: undefined,
    git_repo: undefined,
  };
};
const gitRepoOpts = ref();
const getProductOptions = async () => {
  getProductOpts(productOpts);
  gitRepoOpts.value = await createRepoOptions();
};
function changeRepo(value) {
  createAjax.getData(casesForm.options, value);
}

const activeProductWatcher = () => {
  watch(
    () => formValue.value.product,
    () => {
      getVersionOpts(versionOpts, formValue.value.product);
    }
  );
};

const activeVersionWatcher = () => {
  watch(
    () => formValue.value.version,
    () => {
      getMilestoneOpts(milestoneOpts, formValue.value.version);
    }
  );
};

export default {
  productOpts,
  gitRepoOpts,
  versionOpts,
  milestoneOpts,
  formValue,
  typeOpts,
  ownerOpts,
  rules,
  disabled,
  formRef,
  validateFormData,
  clean,
  getProductOptions,
  changeRepo,
  activeProductWatcher,
  activeVersionWatcher,
};
