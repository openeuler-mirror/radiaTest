import { ref } from 'vue';
import router from '@/router';
import { getCaseReviewDetails, getCaseDetail } from '@/api/get';
import { modifyCommitStatus } from '@/api/put';
import { oldContent, newContent, content } from './content';
import tinymce from 'tinymce/tinymce';
import 'tinymce/themes/silver/theme'; // 引用主题文件
import 'tinymce/icons/default'; // 引用图标文件
import 'tinymce/plugins/image'; //图片
import 'tinymce/plugins/imagetools'; //图片工具
import 'tinymce/plugins/nonbreaking';

// 富文本配置
const init = {
  language_url: require('@/assets/tinymce/zh_CN.js'), // 中文语言包路径
  language: 'zh_CN',
  skin_url: require('tinymce/skins/ui/oxide/skin.css'), // 编辑器皮肤样式
  menubar: false, // 隐藏菜单栏
  height: 200,
  width: '100%',
  toolbar_mode: 'scrolling ', // 工具栏模式
  plugins: 'image imagetools nonbreaking',
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
    reader.onload = function() {
      success(this.result);
    };
  },
};

const detailInfo = ref({});
function detailContent () {
  const oldField = ['description', 'preset', 'steps', 'expection'];
  const newField = ['case_description', 'preset', 'steps', 'expectation'];
  const descriptionField = ['描述', '预置条件', '操作步骤', '预期结果'];
  const result = [];
  oldField.forEach((item, index) => {
    result.push({
      oldContent: String(oldContent.value[item]),
      newContent: String(newContent.value[newField[index]]),
      name: descriptionField[index]
    });
  });
  return result;
}
function getDetail () {
  const commit = router.currentRoute.value.params.commitId;
  getCaseReviewDetails(commit).then(res => {
    detailInfo.value = res.data;
    newContent.value = res.data;
    getCaseDetail({
      id: res.data.case_detail_id
    }).then((response) => {
      [oldContent.value] = response.data;
      content.value = detailContent();
    });
  });
}
const statusTag = {
  pending: 'info',
  open: 'primary',
  rejected: 'error',
  accepted:'success'
};
function handleModify (status) {
  modifyCommitStatus(router.currentRoute.value.params.commitId, { status }).then(() => {
    getDetail();
  });
}
export {
  detailInfo,
  statusTag,
  tinymce,
  init,
  getDetail,
  handleModify
};
