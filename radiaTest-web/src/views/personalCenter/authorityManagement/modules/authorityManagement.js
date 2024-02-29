
import { ref } from 'vue';

const orgList = ref([
  {
    label: '组织1',
    key: '1',
    children: [
      {
        label: '团队1',
        key: '1-1',
        children: [
          {
            label: '人员1',
            key: '1-1-1',
          },
          {
            label: '人员2',
            key: '1-1-2',
          },
        ],
      },
      {
        label: '团队2',
        key: '1-2',
      },
    ],
  },
  {
    label: '组织2',
    key: '2',
    children: [
      {
        label: '团队1',
        key: '2-1',
      },
    ],
  },
]);

const authorityCol = ref([
  {
    title: 'ID',
    key: 'id',
    align: 'left',
  },
  {
    title: '角色',
    key: 'role',
    align: 'center',
  },
  {
    title: '团队',
    key: 'group',
    align: 'center',
  },
]);

const authorityData = ref([
  {
    key: 0,
    id: 'dabukaidehez',
    role: '管理员',
    roleID: 0,
    group: '团队1',
  },
  {
    key: 1,
    id: 'dabukaidehez',
    role: '管理员2',
    roleID: 1,
    group: '团队1',
  },
  {
    key: 2,
    id: 'dabukaidehez',
    role: '管理员3',
    roleID: 2,
    group: '团队1',
  },
  {
    key: 3,
    id: 'dabukaidehez',
    role: '管理员4',
    roleID: 3,
    group: '团队1',
  },
  {
    key: 4,
    id: 'dabukaidehez',
    role: '管理员5',
    roleID: 4,
    group: '团队1',
  },
  {
    key: 5,
    id: 'dabukaidehez',
    role: '管理员6',
    roleID: 5,
    group: '团队1',
  },
  {
    key: 6,
    id: 'dabukaidehez',
    role: '管理员7',
    roleID: 6,
    group: '团队1',
  },
  {
    key: 7,
    id: 'dabukaidehez',
    role: '管理员8',
    roleID: 7,
    group: '团队1',
  },
  {
    key: 8,
    id: 'dabukaidehez',
    role: '管理员9',
    roleID: 8,
    group: '团队1',
  },
  {
    key: 9,
    id: 'dabukaidehez',
    role: '管理员9',
    roleID: 9,
    group: '团队1',
  },
  {
    key: 10,
    id: 'dabukaidehez',
    role: '管理员9',
    roleID: 10,
    group: '团队1',
  },
]);

const authorityPagination = ref({
  pageSizes: [10, 20, 30, 40],
  showQuickJumper: true,
  showSizePicker: true,
});

const showAuthorityModal = ref(false);
const roleValue = ref(3);
const roleOption = ref([
  {
    label: '总管理员',
    value: 0,
  },
  {
    label: '组织管理员',
    value: 1,
  },
  {
    label: '团队管理员',
    value: 2,
  },
  {
    label: '成员',
    value: 3,
  },
]);

function cancelChangeRole() {
  showAuthorityModal.value = false;
}

function changeRoleBtn() {
  showAuthorityModal.value = false;
  console.log(roleValue.value);
}

function authorityRowProps(rowData) {
  return {
    style: 'cursor: pointer;',
    onClick: () => {
      showAuthorityModal.value = true;
      roleValue.value = rowData.roleID;
    },
  };
}

export {
  orgList,
  authorityCol,
  authorityData,
  authorityPagination,
  authorityRowProps,
  showAuthorityModal,
  roleValue,
  roleOption,
  cancelChangeRole,
  changeRoleBtn,
};
