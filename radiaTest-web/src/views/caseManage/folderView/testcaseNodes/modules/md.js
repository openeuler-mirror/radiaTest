import { report } from './details';
const tools =
  'undo redo clear | h bold italic strikethrough quote | ul ol table hr | link image code | todo-list tip ';
const rightTools = 'download preview toc sync-scroll fullscreen';
function downloadMd () {
  let a = document.createElement('a');
  let blob = new Blob([report.value.content]);
  const url = window.URL.createObjectURL(blob);
  a.href = url;
  a.download = `${report.value.name}.md`;
  a.click();
  window.URL.revokeObjectURL(url);
}
const toolbar = {
  download: {
    title: '下载',
    icon: 'iconfont icon-download',
    action () {
      if (report.value.name) {
        downloadMd();
      }
    },
  },
};
export {
  tools,
  rightTools,
  toolbar
};
