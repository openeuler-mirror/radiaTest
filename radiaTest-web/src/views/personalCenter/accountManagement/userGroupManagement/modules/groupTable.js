import { h, ref, reactive } from 'vue';
import { NAvatar, NButton, NDivider, NForm, NInput, NFormItem, NSpace } from 'naive-ui';

import { formatTime } from '@/assets/utils/dateFormatUtils.js';
import axios from '@/axios';
import { changeLoadingStatus } from '@/assets/utils/loading';
import { editGroupUsers } from './groupDrawer';
import { getMsgGroup } from '@/api/get';
import { applyUserGroup } from '@/api/post';
import AvatarGroup from '@/components/personalCenter/avatarGroup.vue';
import textDialog from '@/assets/utils/dialog';

//table base info
const state = reactive({
  editGroupData: {},
  dataList: []
});
const pagination = reactive({
  page: 1,
  pageCount: 1,
  itemCount: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
});

//get table data
function getDataList(name) {
  changeLoadingStatus(true);
  getMsgGroup({
    page_num: pagination.page,
    page_size: pagination.pageSize,
    name
  })
    .then((res) => {
      changeLoadingStatus(false);
      state.dataList = [];
      if (res?.data?.items && Array.isArray(res.data.items) && res.data.items.length) {
        res.data.items.forEach((item) => {
          state.dataList.push({
            name: item.name,
            description: item.description,
            rule: item.re_user_group_role_type === 1 || item.re_user_group_role_type === 2,
            createTime: item.create_time,
            show: false,
            id: item.id,
            avatar_url: item.avatar_url,
            re_user_group_id: item.re_user_group_id,
            re_user_group_role_type: item.re_user_group_role_type,
            admin_awatar: item.admin_awatar,
            user_add_group_flag: item.user_add_group_flag
          });
        });
        pagination.pageCount = res.data.pages;
        pagination.itemCount = res.data.total;
      }
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
      changeLoadingStatus(false);
    });
}

//change table page
function turnPages(page) {
  pagination.page = page;
  getDataList();
}

//change table page size
function turnPageSize(pageSize) {
  pagination.pageSize = pageSize;
  pagination.page = 1;
  getDataList();
}

function groupRowProps(row, rowIndex) {
  return {
    style: 'cursor: pointer;',
    onClick: () => {
      editGroupUsers(rowIndex);
    }
  };
}

//edit group information
const editGroupForm = ref();
const editGroupRules = reactive({
  name: {
    trigger: ['blur', 'input'],
    required: true,
    message: '组织名不能为空'
  }
});
const activeIndex = ref(0);
function editAction(d) {
  const confirmBtn = h(
    NButton,
    {
      type: 'primary',
      ghost: true,
      size: 'large',
      onClick: () => {
        editGroupForm.value.validate((errors) => {
          if (!errors) {
            changeLoadingStatus(true);
            axios
              .put(`/v1/groups/${state.editGroupData.id}`, {
                name: state.editGroupData.name,
                description: state.editGroupData.description
              })
              .then((res) => {
                if (res?.error_code === '2000') {
                  window.$message && window.$message.success('修改成功！');
                  state.dataList[activeIndex.value] = state.editGroupData;
                }
                changeLoadingStatus(false);
                getDataList();
                d.destroy();
              })
              .catch((err) => {
                window.$message && window.$message.error(err.data.error_msg);
                d.destroy();
                changeLoadingStatus(false);
              });
          } else {
            window.$message && window.$message.error('填写信息有误！');
          }
        });
      }
    },
    ['确定']
  );
  const cancelBtn = h(
    NButton,
    {
      type: 'error',
      onClick: () => d.destroy(),
      ghost: true,
      size: 'large'
    },
    ['取消']
  );
  return h(NSpace, { style: 'width:100%' }, [cancelBtn, confirmBtn]);
}
function editContent() {
  const form = h('div', null, [
    h(
      NForm,
      {
        ref: editGroupForm,
        rules: editGroupRules,
        model: state.editGroupData,
        labelPlacement: 'left',
        labelAlign: 'left',
        labelWidth: 100
      },
      [
        h(NFormItem, { label: '用户组名称', path: 'name' }, [
          h(NInput, {
            value: state.editGroupData.name,
            onUpdateValue: (value) => {
              state.editGroupData.name = value;
            }
          })
        ]),
        h(NFormItem, { label: '创建时间' }, [
          h('span', null, [formatTime(new Date(state.editGroupData.createTime), 'yyyy-MM-dd hh:mm:ss')])
        ]),
        h(NFormItem, { label: '描述' }, [
          h(NInput, {
            type: 'textarea',
            value: state.editGroupData.description,
            onUpdateValue: (value) => {
              state.editGroupData.description = value;
            }
          })
        ])
      ]
    )
  ]);
  return form;
}
function handleEdit(rowIndex) {
  state.editGroupData = JSON.parse(JSON.stringify(state.dataList[rowIndex]));
  const d = window.$dialog?.info({
    title: '修改用户组',
    showIcon: false,
    content: () => editContent(),
    action: () => {
      return editAction(d);
    }
  });
}
function handleExit(rowIndex) {
  const d = window.$dialog?.warning({
    title: '提示',
    content: '是否要退出该用户组?',
    showIcon: false,
    action: () => {
      const confirmBtn = h(
        NButton,
        {
          type: 'primary',
          size: 'large',
          ghost: true,
          onClick: () => {
            changeLoadingStatus(true);
            axios.delete(`/v1/groups/${state.dataList[rowIndex].id}`).then((res) => {
              changeLoadingStatus(false);
              if (res.error_code === '2000') {
                window.$message?.success('已成功退出该用户组');
              }
              getDataList();
            });
            d.destroy();
          }
        },
        ['确定']
      );
      const cancelBtn = h(
        NButton,
        {
          type: 'error',
          ghost: true,
          size: 'large',
          onClick: () => {
            d.destroy();
          }
        },
        ['取消']
      );
      return h(
        NSpace,
        {
          style: 'width:100%'
        },
        [cancelBtn, confirmBtn]
      );
    }
  });
}

const handleApply = (row) => {
  textDialog('warning', '确认', '是否申请加入当前用户组', () => {
    applyUserGroup(row.id);
  });
};

//table columns
const columns = [
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
    title: '用户组名称',
    key: 'name',
    align: 'center'
  },
  {
    title: '管理员',
    key: 'admin_awatar',
    align: 'center',
    render(row) {
      let options = row.admin_awatar.map((item) => {
        return { name: item.user_name, src: item.avatar_url };
      });

      return h(AvatarGroup, {
        options,
        size: 40,
        max: 3
      });
    }
  },
  {
    title: '描述',
    key: 'description',
    align: 'center'
  },
  {
    title: '创建时间',
    key: 'createTime',
    align: 'center',
    render(row) {
      return h('span', null, [formatTime(new Date(row.createTime), 'yyyy-MM-dd hh:mm:ss')]);
    }
  },
  {
    title: '操作',
    key: 'operations',
    align: 'center',
    render(row, rowIndex) {
      const edit = h(
        NButton,
        {
          tag: 'span',
          text: true,
          disabled: !row.rule,
          type: 'primary',
          onClick: (event) => {
            if (row.rule) {
              event.stopPropagation();
              handleEdit(rowIndex);
            }
          }
        },
        ['编辑']
      );
      const exit = h(
        NButton,
        {
          tag: 'span',
          text: true,
          type: 'primary',
          onClick: (event) => {
            event.stopPropagation();
            handleExit(rowIndex);
          }
        },
        [row.re_user_group_role_type === 1 ? '解散' : '退出']
      );
      const apply = h(
        NButton,
        {
          tag: 'span',
          text: true,
          type: 'primary',
          onClick: (event) => {
            event.stopPropagation();
            handleApply(row, rowIndex);
          }
        },
        ['申请']
      );
      if (row.user_add_group_flag) {
        return [
          edit,
          h(NDivider, {
            vertical: true
          }),
          exit
        ];
      }
      return apply;
    }
  }
];

export {
  state,
  editGroupForm,
  editGroupRules,
  pagination,
  columns,
  activeIndex,
  getDataList,
  turnPages,
  turnPageSize,
  groupRowProps
};
