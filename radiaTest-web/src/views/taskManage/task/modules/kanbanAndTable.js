import { ref, computed, nextTick } from 'vue';
import store from '@/store/index';
import { showLoading } from './taskDetail.js';
import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';
import { workspace } from '@/assets/config/menu.js';

const listData = ref([]); // 看板数据
const personArray = ref([]); // 执行者
const kanban = computed(() => store.state.taskManage.kanban); // 获取泳道、甘特视图显示状态
const showCreate = ref(true); // 显示新建任务状态
const inputInstRef = ref(null); // 新建任务状态文本框名称
const statusValue = ref(null); // 新建任务状态数据
let giteeId;

// 任务状态数组
const statusArray = computed(() => {
  return listData.value.map((v) => {
    return {
      label: v.statusItem,
      value: v.id
    };
  });
});

// 获取任务信息
function getTask() {
  const allRequest = listData.value.map((item) => {
    return axios.get(`/v1/ws/${workspace.value}/tasks`, {
      status_id: item.id,
      page_num: 1,
      page_size: 99999999
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
  giteeId = Number(storage.getValue('gitee_id'));
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
            tasks: []
          });
        }
        getTask();
        cb && cb();
      } else {
        window.$message?.error(res.errmsg || '未知错误');
      }
    })
    .catch((err) => {
      showLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 泳道菜单
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
        task_ids: value
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

// 泳道拖动回调
function dragChange({ moved }) {
  const orderList = listData.value.map((item, index) => {
    return { name: item.statusItem, order: index + 1 };
  });
  axios
    .put('/v1/task/status/order', {
      order_list: orderList
    })
    .then(() => {
      initData();
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
      [listData.value[moved.newIndex], listData.value[moved.oldIndex]] = [
        listData.value[moved.oldIndex],
        listData.value[moved.newIndex]
      ];
    });
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
        name: str
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
  if (e.draggedContext.element.statusItem === '执行中' || e.draggedContext.element.statusItem === '已执行') {
    return false;
  }
  if (e.willInsertAfter === false && e.relatedContext.element.statusItem === '已执行') {
    return false;
  }
  if (e.willInsertAfter === true && e.relatedContext.element.statusItem === '执行中') {
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

export {
  listData,
  personArray,
  kanban,
  showCreate,
  inputInstRef,
  statusValue,
  statusArray,
  moveList,
  getTask,
  initData,
  selectTools,
  dragChange,
  createStatusLink,
  cancelCreate,
  createStatus,
  toggleComplete2
};
