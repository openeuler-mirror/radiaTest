import { ref, h } from 'vue';
import { NTag, NDropdown, NText, NAvatar } from 'naive-ui';
import { setOrgUserRole } from '@/api/post';
import { getAllRole, getOrgUser } from '@/api/get';
import { deleteOrgUserRole } from '@/api/delete';
import { createAvatar } from '@/assets/utils/createImg';
const activeOrg = ref({});
const showOrgDrawer = ref(false);
const orgDrawerLoading = ref(false);
const allRole = ref({});
const orgDrawerPagination = ref({
  page: 1,
  pageCount: 1,
  pageSize: 10,
});
const orgUsers = ref([]);
function getOrgRole () {
  getAllRole().then(res => {
    res.data.forEach(item => {
      if (item.type === 'org') {
        allRole.value[item.org_id] ?
          allRole.value[item.org_id].push({ label: item.name, value: String(item.id) }) :
          allRole.value[item.org_id] = [{ label: item.name, value: String(item.id) }];
      }
    });
  });
}
function getTableData () {
  orgDrawerLoading.value = true;
  getOrgUser(activeOrg.value.org_id, {
    page_num: orgDrawerPagination.value.page,
    page_size: orgDrawerPagination.value.pageSize
  }).then(res => {
    orgUsers.value = res.data?.items || [];
    orgDrawerPagination.value.pageCount = res.data?.pages || 1;
    orgDrawerLoading.value = false;
  }).catch(() => {
    orgDrawerLoading.value = false;
  });
}
function setActiveOrgInfo (value) {
  showOrgDrawer.value = true;
  activeOrg.value = value;
  getOrgRole();
  getTableData();
}

function drawerUpdateShow (value) {
  showOrgDrawer.value = value;
}
function deleteRole (row) {
  deleteOrgUserRole(activeOrg.value.org_id, {
    user_id: row.gitee_id,
    role_id: row.role.id,
  }).then(() => getTableData());
}
function selectRole (row, item) {
  console.log(item);
  setOrgUserRole(activeOrg.value.org_id, {
    user_id: row.gitee_id,
    role_id: Number(item.value),
  }).then(() => {
    getTableData();
  });
}

const orgDrawerColumns = [
  {
    title: '',
    key: 'avatar_url',
    align: 'center',
    render (row) {
      return h(NAvatar, { size: 'small', src: row.avatar_url, fallbackSrc: createAvatar(row.gitee_name.slice(0,1))});
    }
  },
  {
    title: '用户',
    key: 'gitee_name',
    align: 'center',
  },
  {
    title: '手机号',
    key: 'phone',
    align: 'center'
  },
  {
    title: '角色',
    key: 'role',
    align: 'center',
    render (row) {
      const tag = h(
        NTag,
        {
          type: 'info',
          closable: true,
          onClose: () => deleteRole(row),
        },
        row.role?.name
      );
      const dropList = h(
        NDropdown,
        {
          trigger: 'click',
          options: allRole.value[activeOrg.value.org_id],
          onSelect: (index, item) => selectRole(row, item),
        },
        h(
          NText,
          {
            type: 'info',
            style: `cursor:${allRole.value[activeOrg.value.org_id] ? 'pointer' : 'no-allowed'};color:${allRole.value[activeOrg.value.org_id] ? '' : 'grey'}`,
          },
          '添加角色'
        )
      );
      return row.role ? tag : dropList;
    },
  },
];

export {
  allRole,
  orgUsers,
  orgDrawerColumns,
  activeOrg,
  orgDrawerLoading,
  orgDrawerPagination,
  showOrgDrawer,
  setActiveOrgInfo,
  drawerUpdateShow
};
