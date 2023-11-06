import { ref } from 'vue';
// import { NInput, NSelect, NButton } from 'naive-ui';
import { updateStepLogAxios, updateTask, updateCase } from '@/api/put';
import { getManualJobGroupDetail } from '@/api/get';
import manual from '@/views/testCenter/manual/modules/manual';
import 'tinymce/plugins/autoresize'; //全屏
const showCaseDrawer = ref(false);
const statusOptions = [
  {
    label: '全部',
    value: 4
  },
  {
    label: '执行中',
    value: 2
  },
  {
    label: '成功',
    value: 1
  },
  {
    label: '失败',
    value: 0
  },
  {
    label: '阻塞',
    value: 3
  },
];
const caseDrawerData = ref({});
const selectedCase = ref('');
const fullScreen = ref(false);
// 设置用例结果下拉列表项
const caseOptions = ref([
  {
    label: '成功',
    value: 1,
  },
  {
    label: '失败',
    value: 0,
  },
  {
    label: '阻塞',
    value: 2,
  },
]);
// 用例结果列
const caseResultColumn = [
  {
    key: 'operation',
    title: '测试步骤',
  },
];

//  打开抽屉回调
const showDrawerCb = (row) => {
  showCaseDrawer.value = true;
  caseDrawerData.value.name = row.name;
  getManualCases(row.id);
};
// 获取手工用例
const getManualCases = (id) => {
  getManualJobGroupDetail(id).then((res) => {
    caseDrawerData.value = res.data;
    res.data.all_jobs.forEach(item => {
      item.remark = item.remark || '';
      item.result = item.status === 1 ? item.result : null;
    });
    caseDrawerData.value.cases = res.data.all_jobs;
    activeCaseDetail.value = res.data.all_jobs.length && res.data.all_jobs[0];
  });
};
// 关闭抽屉回调
const closeDrawerCb = () => {
  caseDrawerData.value = {};
  showCaseDrawer.value = false;
  fullScreen.value = false;
  selectedCase.value = '';
  // 调用执行列表
  manual.finishRef.value.getData();
  manual.executeRef.value.getData();

};
// 保存用例步骤
const updateStepLog = (row) => {
  updateStepLogAxios(activeCaseDetail.value.id, {
    step: row.step_num,
    content: row.log_content,
    passed: row.passed,
  });
};
// 结束用例
const endCase = () => {
  let param = {
    remark: activeCaseDetail.value.remark,
    result: activeCaseDetail.value.result,
  };
  updateCase(activeCaseDetail.value.id, param)
    .then(() => {
      getManualCases(caseDrawerData.value.id);
    })
    .catch(() => { });
};
// 结束任务
const handleChangeTask = (value) => {
  let status = value === 0 ? 1 : 0;
  updateTask(caseDrawerData.value.id, { status }).then(() => {
    closeDrawerCb();
  })
    .catch(() => { });
};
// 搜索
const handleFilter = (pattern) => {
  let templatecases = changeValueByStatus(changeSelectValue.value);
  if (pattern) {
    caseDrawerData.value.cases = templatecases.filter((el) => el.case_name.includes(pattern));
  } else {
    caseDrawerData.value.cases = templatecases;
  }
};
const changeSelectValue = ref(null);
const handleUpdateStatus = (value) => {
  changeSelectValue.value = value;
  caseDrawerData.value.cases = changeValueByStatus(value);
};
const changeValueByStatus = (value) => {
  let templatecases;
  //请求接口返回的树数据逻辑
  if (value === 4) {
    templatecases = caseDrawerData.value.all_jobs;
  } else if (value === 3) {
    templatecases = caseDrawerData.value.block_jobs;
  } else if (value === 2) {
    templatecases = caseDrawerData.value.progress_jobs;
  } else if (value === 1) {
    templatecases = caseDrawerData.value.success_jobs;
  } else {
    templatecases = caseDrawerData.value.failed_jobs;
  }
  return templatecases;
};
// 点击左边用例的阴影显示
const activeCaseDetail = ref({});
const handleSelectCase = (testcase) => {
  activeCaseDetail.value = testcase;
  if (selectedCase.value === '') {
    selectedCase.value = testcase.id;
    document.getElementById(`case${selectedCase.value}`).style.boxShadow =
      '0 4px 20px 4px rgba(0, 0, 0, 0.4)';
  } else {
    document.getElementById(`case${selectedCase.value}`).style.boxShadow =
      '0 4px 36px 0 rgba(190, 196, 204, 0.2)';
    selectedCase.value = testcase.id;
    document.getElementById(`case${selectedCase.value}`).style.boxShadow =
      '0 4px 20px 4px rgba(0, 0, 0, 0.4)';
  }
};
// 结束任务switch样式
const railStyle = ({ focused, checked }) => {
  const style = {};
  if (checked) {
    style.background = '#d03050';
    if (focused) {
      style.boxShadow = '0 0 0 2px #d0305040';
    }
  } else {
    style.background = '#2080f0';
    if (focused) {
      style.boxShadow = '0 0 0 2px #2080f040';
    }
  }
  return style;
};
// 富文本配置
const editorInit = {
  selector: '#tinymce',
  language_url: require('@/assets/tinymce/zh_CN.js'), // 中文语言包路径
  language: 'zh_CN',
  skin_url: '/tinymce/skins/ui/oxide', // 编辑器皮肤样式
  content_css: '/tinymce/skins/content/default/content.min.css',
  menubar: false, // 隐藏菜单栏
  height: 400,
  width: '100%',
  toolbar_mode: 'scrolling', // 工具栏模式
  plugins: 'image imagetools nonbreaking  autoresize',
  toolbar:
    'undo redo fontsizeselect fontselect|underline forecolor backcolor bold italic strikethrough image subscript superscript removeformat|',
  content_style: 'p {margin: 5px 0; font-size: 14px}',
  fontsize_formats: '12px 14px 16px 18px 24px 36px 48px 56px 72px',
  font_formats:
    '微软雅黑=Microsoft YaHei,Helvetica Neue,PingFang SC,sans-serif;苹果苹方=PingFang SC,Microsoft YaHei,sans-serif;宋体=simsun,serif;仿宋体=FangSong,serif;黑体=SimHei,sans-serif;Arial=arial,helvetica,sans-serif;Arial Black=arial black,avant garde;Book Antiqua=book antiqua,palatino;',
  branding: false, // 隐藏右下角技术支持
  elementpath: false, // 隐藏底栏的元素路径
  nonbreaking_force_tab: true,
  resize: false, // 禁止改变大小
  statusbar: false, // 隐藏底部状态栏
  // 图片上传
  images_upload_handler(blobInfo, success) {
    let reader = new FileReader();
    reader.readAsDataURL(blobInfo.blob());
    reader.onload = function () {
      success(this.result);
    };
  },
};

export default {
  statusOptions,
  showCaseDrawer,
  caseDrawerData,
  selectedCase,
  caseOptions,
  caseResultColumn,
  activeCaseDetail,
  fullScreen,
  showDrawerCb,
  closeDrawerCb,
  updateStepLog,
  handleSelectCase,
  endCase,
  railStyle,
  handleChangeTask,
  handleFilter,
  handleUpdateStatus,
  editorInit
};
