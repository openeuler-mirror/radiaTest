import { ref, computed, nextTick, toRef, h } from 'vue';
import store from '@/store/index';
import { showLoading, getDetail } from './taskDetail.js';
import { NAvatar } from 'naive-ui';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';

const listData = ref([]); // 看板数据
const personArray = ref([]); // 执行者
const kanban = toRef(store.state.taskManage, 'kanban'); // 获取看板、表格视图显示状态
const showCreate = ref(true); // 显示新建任务状态
const inputInstRef = ref(null); // 新建任务状态文本框名称
const statusValue = ref(null); // 新建任务状态数据
let giteeId;

// 任务状态数组
const statusArray = computed(() => {
  return listData.value.map((v) => {
    return {
      label: v.statusItem,
      value: v.id,
    };
  });
});

// 表格视图列选项
const columns = ref([
  {
    title: '任务名称',
    key: 'statusItem',
    render(row) {
      if (row.statusItem) {
        return row.statusItem;
      }
      return row.title;
    },
  },
  {
    title: '创建者',
    key: 'owner',
    align: 'center',
    render(row) {
      const avatar = h(NAvatar, {
        src: row.originator?.avatar_url,
        style: 'margin-right:5px',
        round: true,
      });
      return h(
        'div',
        {
          style: 'display:flex;align-items:center;justify-content:center;',
        },
        [avatar, row.originator?.gitee_name]
      );
    },
  },
  {
    title: '截止日期',
    key: 'deadline',
    align: 'center',
    render(row) {
      if (row.deadline) {
        return formatTime(row.deadline, 'yyyy-MM-dd hh:mm:ss');
      }
      return '';
    },
  },
]);

// 获取任务信息
function getTask() {
  const allRequest = listData.value.map((item) => {
    return axios.get('/v1/tasks', {
      status_id: item.id,
      page_num: 1,
      page_size: 99999999,
    });
  });
  Promise.allSettled(allRequest)
    .then((results) => {
      results.forEach((item, index) => {
        if (item?.value?.data?.items?.length) {
          listData.value[index].tasks = item.value.data.items;
        }
      });
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 初始化数据
function initData(cb) {
  giteeId=Number(storage.getValue('gitee_id'));
  showLoading.value = true;
  axios
    .get('/v1/task/status')
    .then((res) => {
      showLoading.value = false;
      if (res.data) {
        listData.value = [];
        for (const item of res.data) {
          listData.value.push({
            statusItem: item.name,
            id: item.id,
            order: item.order,
            tasks: [],
          });
        }
        getTask();
        cb&&cb();
      } else {
        window.$message?.error(res.errmsg || '未知错误');
      }
    })
    .catch((err) => {
      showLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 甬道菜单
function selectTools({ key, value }, element) {
  if (key === 'delete') {
    showLoading.value = true;
    axios
      .delete(`/v1/task/status/${element.id}`)
      .then(() => {
        window.$message?.success('删除成功!');
        showLoading.value = false;
        initData();
      })
      .catch((err) => {
        showLoading.value = false;
        window.$message?.error(err.data.error_msg || '未知错误');
      });
  } else if (key === 'edit') {
    showLoading.value = true;
    axios
      .put(`/v1/task/status/${element.id}`, { name: value })
      .then(() => {
        showLoading.value = false;
        element.statusItem = value;
      })
      .catch((err) => {
        window.$message?.error(err.data.error_msg || '未知错误');
        initData();
      });
  } else if (key === 'deleteTasks') {
    showLoading.value = true;
    axios
      .put('/v1/tasks/list', {
        task_ids: value,
      })
      .then(() => {
        showLoading.value = false;
        initData();
      })
      .catch((err) => {
        window.$message?.error(err.data.error_msg || '未知错误');
      });
  }
}

// 甬道拖动回调
function dragChange({ moved }) {
  const orderList = listData.value.map((item, index) => {
    return { name: item.statusItem, order: index + 1 };
  });
  axios
    .put('/v1/task/status/order', {
      order_list: orderList,
    })
    .then(() => {
      initData();
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
      [listData.value[moved.newIndex], listData.value[moved.oldIndex]] = [
        listData.value[moved.oldIndex],
        listData.value[moved.newIndex],
      ];
    });
}

// 设置表格视图行数据key
function listRowKey(rowData) {
  return rowData.id;
}

// 表格视图行数据点击回调
function rowProps(rowData) {
  return {
    style: 'cursor: pointer;',
    onClick: (e) => {
      if (!rowData.statusItem) {
        const iconNode = ['path', 'svg'];
        if (iconNode.includes(e.target.nodeName.toLocaleLowerCase())) {
          if (rowData.tasks.length === 0) {
            axios.get(`/v1/tasks/${rowData.id}`).then((res) => {
              if (res.data?.child_tasks) {
                rowData.tasks = res.data.child_tasks.map((item) => {
                  return {
                    avatar: item.originator_avatar_url,
                    closingTime: item.deadline,
                    id: item.id,
                    owner: item.originator_name,
                    name: item.title,
                    tasks: [],
                    level: item.level,
                  };
                });
              } else {
                rowData.tasks = [];
              }
            });
          }
        } else {
          getDetail(rowData);
        }
      }
    },
  };
}

// 点击新建任务状态
function createStatusLink() {
  showCreate.value = false;
  nextTick(() => {
    inputInstRef.value.focus();
  });
}

// 取消新建任务状态
function cancelCreate() {
  showCreate.value = true;
}

// 保存新建人物状态
function createStatus(str) {
  if (str) {
    showLoading.value = true;
    axios
      .post('/v1/task/status', {
        name: str,
      })
      .then(() => {
        showLoading.value = false;
        window.$message?.success('添加成功!');
        initData();
      })
      .catch((err) => {
        showLoading.value = false;
        window.$message?.error(err.data.error_msg || '未知错误');
      });
    showCreate.value = true;
  }
}
function moveList(e) {
  if (
    e.draggedContext.element.statusItem === '执行中' ||
    e.draggedContext.element.statusItem === '已执行'
  ) {
    return false;
  }
  if (
    e.willInsertAfter === false &&
    e.relatedContext.element.statusItem === '已执行'
  ) {
    return false;
  }
  if (
    e.willInsertAfter === true &&
    e.relatedContext.element.statusItem === '执行中'
  ) {
    return false;
  }
  return true;
}

const tempData = ref([]);

function toggleComplete2($event) {
  if ($event) {
    listData.value.forEach((v) => {
      if (v.id === 5) {
        v.tasks = tempData.value;
      }
    });
  } else {
    listData.value.forEach((v) => {
      if (v.id === 5) {
        tempData.value = v.tasks;
        let tempArr = [];
        console.log(v.tasks);
        v.tasks.forEach((task) => {
          if (task?.executor?.gitee_id === giteeId) {
            tempArr.push(task);
          }
        });
        v.tasks = tempArr;
      }
    });
  }
}
// function filterTask (filterValue) {
//   let listDataTemp;
//   const temp = JSON.parse(JSON.stringify(filterValue));
//   console.log(temp);
//   if (temp.status_id) {
//     listDataTemp = listData.value;
//     listData.value = listData.value.filter((item) => {
//       return item.id === temp.status_id;
//     });
//   } else {
//     listData.value = listDataTemp
//       ? listDataTemp
//       : listData.value;
//   }
//   if (temp.participant_id?.length) {
//     temp.participant_id = temp.participant_id.join(',');
//   }
//   const allRequest = listData.value.map((item) => {
//     return axios.get('/v1/tasks', {
//       ...temp,
//       status_id: item.id,
//     });
//   });
//   Promise.allSettled(allRequest)
//     .then((results) => {
//       results.forEach((item, index) => {
//         listData.value[index].tasks = [];
//         if (item?.value?.data?.items?.length) {
//           listData.value[index].tasks = item.value.data.items;
//         }
//         kanban.showTaskList = true;
//       });
//     });
// }

export {
  listData,
  personArray,
  kanban,
  showCreate,
  inputInstRef,
  statusValue,
  statusArray,
  columns,
  moveList,
  getTask,
  initData,
  selectTools,
  dragChange,
  listRowKey,
  rowProps,
  createStatusLink,
  cancelCreate,
  createStatus,
  toggleComplete2,
};
