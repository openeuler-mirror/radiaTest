<template>
  <n-drawer
    v-model:show="showResultDrawer"
    :width="1000"
    class="caseDrawerContainer"
    @afterLeave="closeResultDrawerCb"
  >
    <n-drawer-content id="drawer-result-target">
      <template #header>
        <div class="header">
          <n-button @click="closeResultDrawerCb" class="backIcon" size="medium" quaternary circle>
            <n-icon :size="26">
              <arrow-left />
            </n-icon>
          </n-button>
          <div>结果统计</div>
        </div>
      </template>
      <div class="drawerContent">
        <n-scrollbar style="max-height: 100%">
          <div class="contentWrap">
            <n-card title="▍概览" header-style="padding: 10px;">
              <div>
                <div class="contentLine">
                  <div>
                    <span class="leftTitle">任务名：</span><span>{{ caseDrawerData.name }}</span>
                  </div>
                  <div>
                    <span class="leftTitle">测试时间：</span
                    ><span>{{ formatTime(caseDrawerData.update_time) }}</span>
                  </div>
                  <div>
                    <span class="leftTitle">测试总数：</span><span>{{ caseDrawerData.total }}</span>
                  </div>
                </div>
                <div class="contentLine">
                  <div>
                    <span class="leftTitle">失败数：</span><span>{{ caseDrawerData.failed }}</span>
                  </div>
                  <div>
                    <span class="leftTitle">成功数：</span><span>{{ caseDrawerData.success }}</span>
                  </div>
                  <div>
                    <span class="leftTitle">阻塞数：</span><span>{{ caseDrawerData.block }}</span>
                  </div>
                </div>

                <div class="contentLine">
                  <div>
                    <span class="leftTitle">未完成数：</span
                    ><span>{{ caseDrawerData.progress }}</span>
                  </div>
                  <div>
                    <span class="leftTitle">执行完成率：</span
                    ><span>{{ caseDrawerData.finished_rate }}</span>
                  </div>
                  <div>
                    <span class="leftTitle">通过率：</span
                    ><span>{{ caseDrawerData.success_rate }}</span>
                  </div>
                </div>
              </div>
            </n-card>
            <n-card
              title="▍功能用例统计分析"
              header-style="padding: 10px;"
              style="margin-top: 20px"
            >
              <n-tabs
                type="line"
                size="large"
                :tabs-padding="20"
                pane-style="padding: 20px;"
                @update:value="handleUpdateValue"
              >
                <template v-for="item in staticCases" :key="item.name">
                  <n-tab-pane :name="item.name" :tab="item.tab">
                    <n-data-table remote :columns="caseStaticColumn" :data="caseTableData" />
                  </n-tab-pane>
                </template>
              </n-tabs>
            </n-card>
            <n-card title="▍报告总结" header-style="padding: 10px;" style="margin-top: 20px">
              <Editor v-model="caseDrawerData.report" tag-name="div" :init="editorInit" />
              <div class="btnWrap">
                <n-button class="btn" type="info" @click="saveResultCount" v-show="!hasFinished"
                  >报告保存</n-button
                >
              </div>
            </n-card>
          </div>
        </n-scrollbar>
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script setup>
import { ref } from 'vue';
import { ArrowLeft32Filled as ArrowLeft } from '@vicons/fluent';
import Editor from '@tinymce/tinymce-vue';
import { NTag } from 'naive-ui';
import { getManualJobGroupDetail } from '@/api/get';
import { saveManualText } from '@/api/post';
import 'tinymce/plugins/autoresize'; //全屏
const caseDrawerData = ref({});

// 富文本配置
const editorInit = {
  language_url: require('@/assets/tinymce/zh_CN.js'), // 中文语言包路径
  language: 'zh_CN',
  skin_url: '/tinymce/skins/ui/oxide', // 编辑器皮肤样式
  content_css: '/tinymce/skins/content/default/content.min.css',
  menubar: false, // 隐藏菜单栏
  height: 400,
  width: '100%',
  toolbar_mode: 'scrolling', // 工具栏模式
  plugins: 'image imagetools nonbreaking autoresize',
  toolbar:
    'undo redo fontsizeselect fontselect|underline forecolor backcolor bold italic strikethrough image subscript superscript removeformat|',
  content_style: 'p {margin: 5px 0; font-size: 14px}',
  fontsize_formats: '12px 14px 16px 18px 24px 36px 48px 56px 72px',
  font_formats:
    '微软雅黑=Microsoft YaHei,Helvetica Neue,PingFang SC,sans-serif;苹果苹方=PingFang SC,Microsoft YaHei,sans-serif;宋体=simsun,serif;仿宋体=FangSong,serif;黑体=SimHei,sans-serif;Arial=arial,helvetica,sans-serif;Arial Black=arial black,avant garde;Book Antiqua=book antiqua,palatino;',
  branding: false, // 隐藏右下角技术支持
  elementpath: false, // 隐藏底栏的元素路径
  nonbreaking_force_tab: true,
  resize: true, // 禁止改变大小
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

// 功能用例统计分析切换tab
const staticCases = [
  { name: 'all', tab: '所有用例' },
  { name: 'faile', tab: '失败用例' },
  { name: 'success', tab: '成功用例' },
  { name: 'block', tab: '阻塞用例' },
  { name: 'process', tab: '未完成用例' },
];
const handleUpdateValue = (value) => {
  if (value === 'all') {
    caseTableData.value = caseDrawerData.value.all_jobs;
  } else if (value === 'success') {
    caseTableData.value = caseDrawerData.value.success_jobs;
  } else if (value === 'faile') {
    caseTableData.value = caseDrawerData.value.failed_jobs;
  } else if (value === 'block') {
    caseTableData.value = caseDrawerData.value.block_jobs;
  } else {
    caseTableData.value = caseDrawerData.value.progress_jobs;
  }
};
const caseStaticColumn = [
  {
    key: 'case_name',
    title: '名称',
    align: 'center',
  },
  {
    key: 'executor_name',
    title: '执行人',
    align: 'center',
  },
  {
    key: 'status',
    title: '状态',
    align: 'center',
    render: (row) => (row.status === 1 ? '已执行' : '未执行'),
  },
  {
    key: 'result',
    title: '执行结果',
    align: 'center',
    render(row) {
      return h(
        NTag,
        {
          type: getRowResult(row).split('-')[1],
          round: true,
        },
        getRowResult(row).split('-')[0]
      );
    },
  },
  {
    key: 'end_time',
    title: '更新时间',
    align: 'center',
    render: (row) => formatTime(row.end_time),
  },
];
const caseTableData = ref([]);

/****************抽屉相关*************/
const showResultDrawer = ref(false);
// 打开抽屉回调
const manualTaskId = ref(null);
const showResultDrawerCb = (row) => {
  showResultDrawer.value = true;
  manualTaskId.value = row.id;
  getManualJobGroupDetail(row.id).then((res) => {
    caseDrawerData.value = res.data;
    caseTableData.value = res.data.all_jobs;
    caseDrawerData.value.report = caseDrawerData.value.report || '';
  });
};

const getRowResult = (row) => {
  let result;
  let status;
  if (row.result === 1) {
    result = '成功';
    status = 'success';
  } else if (row.result === 0 && row.status === 1) {
    result = '失败';
    status = 'error';
  } else if (row.result === 2 && row.status === 1) {
    result = '阻塞';
    status = 'warning';
  } else {
    result = '未执行';
    status = 'error';
  }
  return `${result}-${status}`;
};

// 关闭抽屉回调
const closeResultDrawerCb = () => {
  caseDrawerData.value = {};
  showResultDrawer.value = false;
};
const saveResultCount = () => {
  saveManualText(manualTaskId.value, { report: caseDrawerData.value.report })
    .then(() => {
      window.$message?.success('保存成功');
      closeResultDrawerCb();
    })
    .catch(() => {});
};
const formatTime = (time) => {
  return time
    ? new Date(time).toLocaleString('zh-CN', { hourCycle: 'h23' }).replace(/\//g, '-')
    : 0;
};
defineExpose({
  showResultDrawerCb,
});
</script>
<style scoped lang="less">
.caseDrawerContainer {
  .header {
    display: flex;
    align-items: center;

    .backIcon {
      margin-right: 20px;
    }
  }

  .drawerContent {
    width: 100%;
    height: 100%;
    .contentWrap {
      width: 100%;
      height: calc(100% - 45px);
      .contentLine {
        margin-top: 10px;
        display: flex;
        justify-content: space-between;
        .leftTitle {
          color: #222121;
        }
      }
    }

    .btnWrap {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 50px;

      .btn {
        margin: 0 10px;
      }
    }
  }
}
</style>
