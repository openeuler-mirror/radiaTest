import { ref, reactive, h } from 'vue';

import axios from '@/axios';
import { generateMDByTemplate } from './utils/generateMD';
import { showReportModal, getMdFiles } from './taskDetail';
import { NButton, NInput } from 'naive-ui';
import { getTaskReports } from '@/api/get';

const tools =
  'undo redo clear | h bold italic strikethrough quote | ul ol table hr | link image code | todo-list tip | save';
const rightTools = 'download preview toc sync-scroll fullscreen';

const previewShow = ref(false);
function previewMd() {
  previewShow.value = true;
}

const md = reactive({
  name: '',
  content: '',
  taskId: '',
});
async function generateMdFile(taskId, isVersionTask) {
  try {
    md.taskId = taskId;
    const data = await getTaskReports(taskId);
    md.content = await generateMDByTemplate(isVersionTask);
    md.name = data.data?.title ? `${data.data.title}.md` : '';
    showReportModal.value = true;
  } catch (error) {
    window.$message?.error(error.statusText || '未知错误');
  }
}

function downloadMd() {
  let a = document.createElement('a');
  let blob = new Blob([md.content]);
  const url = window.URL.createObjectURL(blob);
  a.href = url;
  a.download = `${md.name}.md`;
  a.click();
  window.URL.revokeObjectURL(url);
}

const previewWidth = window.innerWidth * 0.8;
const previewHeight = window.innerHeight * 0.8;

function generateDailog() {
  return new Promise((resolve, reject) => {
    const d = window.$dialog?.info({
      title: '报告名称',
      content: () => {
        return h(NInput, {
          placeholder: '请输入报告名称',
          onUpdateValue(value) {
            md.name = value;
          },
        });
      },
      action() {
        return h(
          NButton,
          {
            type: 'primary',
            onClick() {
              if (md.name) {
                d.destroy();
                resolve();
              } else {
                window.$message?.error('请填写报告名称');
                reject(new Error('请填写报告名称'));
              }
            },
          },
          '确定'
        );
      },
    });
  });
}
function saveFileAction() {
  axios
    .put(`/v1/tasks/${md.taskId}/reports`, {
      title: md.name,
      content: md.content,
    })
    .then(() => {
      window.$message?.success('保存成功!');
      getMdFiles();
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}
function saveFile() {
  if (md.name) {
    saveFileAction();
  } else {
    generateDailog().then(() => {
      saveFileAction();
    });
  }
}

const toolbar = {
  download: {
    title: '下载',
    icon: 'iconfont icon-download',
    action() {
      if (md.name) {
        downloadMd();
      } else {
        generateDailog().then(() => {
          downloadMd();
        });
      }
    },
  },
  // save: {
  //   title: '保存',
  //   icon: 'v-md-icon-save',
  //   action () {
  //     if (md.name) {
  //       saveFile();
  //     } else {
  //       generateDailog().then(() => {
  //         saveFile();
  //       });
  //     }

  //   }
  // }
};

export {
  toolbar,
  previewWidth,
  rightTools,
  previewHeight,
  tools,
  md,
  previewShow,
  saveFile,
  generateMdFile,
  previewMd,
  downloadMd,
};
