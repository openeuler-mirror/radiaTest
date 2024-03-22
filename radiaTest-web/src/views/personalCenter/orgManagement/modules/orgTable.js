import { h, ref } from 'vue';
import { NAvatar, NIcon, NButton, NSpace } from 'naive-ui';
import { Construct } from '@vicons/ionicons5';
import { renderTooltip } from '@/assets/render/tooltip';
import { Delete24Regular as Delete } from '@vicons/fluent';
import { registerModel, showRegisterOrgWindow, isCreate, fileList } from './registerOrg';
import { organizationInfo } from '@/api/put';
import { getAdminOrg } from '@/api/get';
import textDialog from '@/assets/utils/dialog';

const orgs = ref([]);
function getData() {
  getAdminOrg().then((res) => {
    orgs.value = res.data;
  });
}

function cloneRegisterModel(row) {
  for (const key in row.cla_verify_params) {
    registerModel.urlParams.push({ key, value: row.cla_verify_params[key] });
  }
  for (const key in row.cla_verify_body) {
    registerModel.bodyParams.push({ key, value: row.cla_verify_body[key] });
  }
  const cloneData = JSON.parse(JSON.stringify(row));
  Object.keys(cloneData).forEach((key) => {
    if (!cloneData[key]) {
      cloneData[key] = undefined;
    }
  });
  if (cloneData.authority === 'oneid') {
    registerModel.authorityType = 'oneid';
  } else if (cloneData.authority === 'gitee' && cloneData.enterprise_id) {
    registerModel.authorityType = 'gitee';
    registerModel.authoritySecondaryType = 'enterprise';
  } else {
    registerModel.authorityType = 'gitee';
    registerModel.authoritySecondaryType = 'personal';
  }

  registerModel.name = cloneData.name;
  registerModel.enterpriseId = cloneData.enterprise_id;
  registerModel.enterpriseToken = cloneData.enterprise_token;
  registerModel.enterpriseJoinUrl = cloneData.enterprise_join_url;
  registerModel.oauthClientId = cloneData.oauth_client_id;
  registerModel.oauthClientSecret = cloneData.oauth_client_secret;
  registerModel.oauthClientScope = cloneData.oauth_scope?.split(',');
  registerModel.description = cloneData.description;
  registerModel.orgId = cloneData.organization_id;
  registerModel.organizationSvatar = cloneData.avatar_url;
  registerModel.oauthLoginUrl = cloneData.oauth_login_url;
  registerModel.oauthGetTokenUrl = cloneData.oauth_get_token_url;
  registerModel.oauthGetUserInfoUrl = cloneData.oauth_get_user_info_url;
  fileList.value = [];
  if (row.avatar_url) {
    fileList.value.push({ id: 'c', status: 'finished', url: row.avatar_url });
  }
}

function handleDeleteOrg(row) {
  textDialog('warning', '删除组织', '您确定要删除此组织吗？', () => {
    let deleteFormData = new FormData();
    deleteFormData.append('is_delete', true);
    organizationInfo(row.organization_id, deleteFormData).finally(() => {
      getData();
    });
  });
}

const orgColumns = [
  {
    title: '',
    key: 'avatar_url',
    align: 'center',
    render(row) {
      return h(NAvatar, {
        size: 'small',
        src: row.avatar_url,
        style: { background: 'rgba(0,0,0,0)' }
      });
    }
  },
  {
    title: '组织名称',
    key: 'name',
    align: 'center'
  },
  {
    title: '描述',
    key: 'description',
    align: 'center'
  },
  {
    title: '操作',
    key: 'action',
    align: 'center',
    render: (row) => {
      return h(
        NSpace,
        {
          justify: 'center',
          align: 'center'
        },
        [
          renderTooltip(
            h(
              NButton,
              {
                size: 'medium',
                type: 'warning',
                circle: true,
                onClick: () => {
                  isCreate.value = false;
                  showRegisterOrgWindow.value = true;
                  cloneRegisterModel(row);
                }
              },
              h(NIcon, { size: '20' }, h(Construct))
            ),
            '修改'
          ),
          renderTooltip(
            h(
              NButton,
              {
                size: 'medium',
                type: 'error',
                circle: true,
                onClick: () => {
                  handleDeleteOrg(row);
                }
              },
              h(NIcon, { size: '20' }, h(Delete))
            ),
            '删除'
          )
        ]
      );
    }
  }
];
const pagination = {
  pagesize: 7
};

export { orgs, pagination, orgColumns, getData };
