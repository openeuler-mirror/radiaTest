<template>
  <div class="manualContainer">
    <div style="width: 100%">
      <div id="execute">
        <n-grid :cols="24" y-gap="20">
          <n-gi :span="24">
            <div class="title">{{ executingTaskNum || 0 }} 个任务正在执行</div>
          </n-gi>
          <n-gi :span="16">
            <label class="secondTitle">
              每页
              <n-select
                :options="pageSizeOptions"
                @update:value="changeExecutingTaskPagesize"
                class="selectNum"
                size="small"
                clearable
              />
              个任务
            </label>
          </n-gi>
          <!-- <n-gi :span="8">
            <n-input
              v-model:value="executingTaskSearch"
              placeholder="搜索任务名......"
              size="large"
              class="searchInput"
              round
            />
          </n-gi> -->
          <n-gi :span="24">
            <n-data-table
              remote
              :columns="executingTaskColumns"
              :data="executingTaskData"
              :pagination="executingTaskPagination"
              @update:page="executingTaskPageChange"
              :row-props="executingTaskRowProps"
            />
          </n-gi>
        </n-grid>
      </div>
      <div id="finish">
        <n-grid :cols="24" y-gap="20">
          <n-gi :span="24">
            <div class="title">{{ finishedTaskNum || 0 }} 个任务已完成</div>
          </n-gi>
          <n-gi :span="16">
            <label class="secondTitle">
              每页
              <n-select
                :options="pageSizeOptions"
                @update:value="changefinishedTaskPagesize"
                class="selectNum"
                size="small"
                clearable
              />
              个任务
            </label>
          </n-gi>
          <!-- <n-gi :span="8">
            <n-input
              v-model:value="finishedTaskSearch"
              placeholder="搜索任务名......"
              size="large"
              class="searchInput"
              round
            />
          </n-gi> -->
          <n-gi :span="24">
            <n-data-table
              remote
              :columns="finishedTaskColumns"
              :data="finishedTaskData"
              :pagination="finishedTaskPagination"
              @update:page="finishedTaskPageChange"
            />
          </n-gi>
        </n-grid>
      </div>
    </div>
    <div class="anchorWrap">
      <n-anchor affix :trigger-top="24" :top="88" class="anchor" :bound="24" offset-target="#homeBody">
        <n-anchor-link title="执行队列" href="#execute" />
        <n-anchor-link title="执行结果" href="#finish" />
      </n-anchor>
      <n-popover trigger="hover">
        <template #trigger>
          <div class="createJobBtn" @click="clickCreateJobBtn">
            <n-icon :size="80">
              <FileAddOutlined />
            </n-icon>
          </div>
        </template>
        <span>创建手工测试任务</span>
      </n-popover>
    </div>
  </div>
  <n-drawer v-model:show="showCaseDrawer" class="caseDrawerContainer" @afterLeave="closeDrawerCb">
    <n-drawer-content id="drawer-target">
      <template #header>
        <div class="header">
          <n-button @click="exitDrawer" class="backIcon" size="medium" quaternary circle>
            <n-icon :size="26">
              <arrow-left />
            </n-icon>
          </n-button>
          <div>{{ caseDrawerData.name }}</div>
        </div>
      </template>
      <div class="drawer-content">
        <n-collapse :default-expanded-names="['1', '2', '3', '4']">
          <n-collapse-item title="用例描述&预置条件" name="1">
            <div class="contentWrap">
              <div>{{ caseDrawerData.case_description }}</div>
              <div>{{ caseDrawerData.case_preset }}</div>
              <n-steps v-model:current="currentStep" @update:current="changeSetp" class="stepWrap">
                <n-step v-for="i in caseDrawerData.total_step" :key="i"></n-step>
              </n-steps>
            </div>
          </n-collapse-item>
          <n-collapse-item title="操作步骤" name="2">
            <pre class="contentWrap">{{ caseDrawerData.operation }}</pre>
          </n-collapse-item>
          <n-collapse-item title="实际结果" name="3">
            <template #header-extra>
              <n-button
                tertiary
                round
                type="info"
                size="tiny"
                color="#6e767e"
                @click.stop="editResult"
                v-show="!hasFinished"
              >
                {{ showEditor ? '退出' : '编辑' }}
              </n-button></template
            >
            <div class="contentWrap">
              <div v-html="commentInput" v-show="!showEditor" class="commentWrap"></div>
              <div v-show="showEditor">
                <Editor v-model="commentInput" tag-name="div" :init="init" />
              </div>
            </div>
          </n-collapse-item>
          <n-collapse-item title="预期结果" name="4">
            <div class="contentWrap">
              <div>{{ caseDrawerData.case_expection }}</div>
              <n-radio-group v-model:value="expectResult" name="radiogroup" :disabled="hasFinished" class="radioWrap">
                <n-space>
                  <n-radio :value="true"> 结果一致 </n-radio>
                  <n-radio :value="false"> 预期不符 </n-radio>
                </n-space>
              </n-radio-group>
            </div>
          </n-collapse-item>
        </n-collapse>
        <div class="btnWrap">
          <n-button class="btn" @click="exitDrawer">退出</n-button>
          <n-button class="btn" type="info" @click="updateStepLog" v-show="!hasFinished">保存</n-button>
          <n-button
            class="btn"
            type="success"
            v-show="caseDrawerData.current_step === caseDrawerData.total_step && !hasFinished"
            @click="submitStepLog"
            >完成执行</n-button
          >
        </div>
      </div>
    </n-drawer-content>
  </n-drawer>
  <ManualCreateModal ref="manualCreateModalRef" @updateTable="getExecutingTask"></ManualCreateModal>
</template>

<script setup>
import { NTag, NButton, NIcon, NSpace, NProgress } from 'naive-ui';
import { CheckCircle } from '@vicons/fa';
import { FileAddOutlined } from '@vicons/antd';
import { CancelFilled } from '@vicons/material';
import { ArrowLeft32Filled as ArrowLeft, Delete24Regular as Delete } from '@vicons/fluent';
import ManualCreateModal from '@/views/testCenter/components/ManualCreateModal.vue';
import { renderTooltip } from '@/assets/render/tooltip';
import textDialog from '@/assets/utils/dialog';
import { any2standard } from '@/assets/utils/dateFormatUtils';
import Editor from '@tinymce/tinymce-vue';
import { deleteManualJob } from '@/api/delete';
import { getManualJob, getManualJobLog } from '@/api/get';
import { updateStepLogAxios } from '@/api/put';
import { submitManualJob } from '@/api/post';
import _ from 'lodash';

const executingTaskNum = ref(0);
const finishedTaskNum = ref(0);
const pageSizeOptions = [
  { label: '5', value: 5 },
  { label: '10', value: 10 },
  { label: '20', value: 20 },
  { label: '50', value: 50 }
];
const executingTaskPagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1
});
// const executingTaskSearch = ref('');
const executingTaskColumns = [
  {
    key: 'case_id',
    title: '编号',
    align: 'center'
  },
  {
    key: 'name',
    title: '名称',
    align: 'center'
  },
  {
    key: 'milestone_name',
    title: '里程碑',
    align: 'center'
  },
  {
    key: 'executor_name',
    title: '执行人',
    align: 'center'
  },
  {
    key: 'progress',
    title: '执行进度',
    align: 'center',
    render: (row) => {
      return h(NProgress, {
        type: 'line',
        percentage: Math.round((row.current_step / row.total_step) * 100),
        indicatorPlacement: 'inside',
        processing: true
      });
    }
  },
  {
    key: 'start_time',
    title: '开始时间',
    align: 'center'
  },
  {
    key: 'status',
    title: '当前状态',
    align: 'center',
    width: 100,
    fixed: 'right',
    render: () => {
      return h(
        NTag,
        {
          type: 'info',
          round: true
        },
        'Testing'
      );
    }
  },
  {
    title: '操作',
    align: 'center',
    fixed: 'right',
    render: (row) => {
      return h(
        NSpace,
        {
          justify: 'center',
          align: 'center'
        },
        [
          renderTooltip(
            h(
              NButton,
              {
                size: 'medium',
                type: 'error',
                circle: true,
                onClick: (e) => {
                  e.stopPropagation();
                  textDialog('warning', '警告', '确认删除手工测试任务？', () => {
                    deleteManualJob(row.id).then(() => {
                      executingTaskPagination.value.page = 1;
                      getExecutingTask();
                    });
                  });
                }
              },
              h(NIcon, { size: '20' }, h(Delete))
            ),
            '删除'
          )
        ]
      );
    }
  }
];
const executingTaskData = ref([]);

const executingTaskPageChange = (page) => {
  executingTaskPagination.value.page = page;
  getExecutingTask();
};

const changeExecutingTaskPagesize = (value) => {
  executingTaskPagination.value.pageSize = value || 10;
  executingTaskPagination.value.page = 1;
  getExecutingTask();
};

// 打开日志抽屉回调
const showDrawerCb = (row) => {
  caseDrawerData.value = _.cloneDeep(row);
  showCaseDrawer.value = true;
  if (caseDrawerData.value.current_step === 0) {
    caseDrawerData.value.current_step = 1;
  }
  currentStep.value = caseDrawerData.value.current_step;
  getJobLog(caseDrawerData.value.id, caseDrawerData.value.current_step);
};

// 点击进行中任务
const executingTaskRowProps = (row) => {
  return {
    style: 'cursor: pointer;',
    onClick: () => {
      showDrawerCb(row);
    }
  };
};

const getExecutingTask = () => {
  getManualJob({
    status: 0,
    page_num: executingTaskPagination.value.page,
    page_size: executingTaskPagination.value.pageSize
  }).then((res) => {
    executingTaskData.value = [];
    executingTaskPagination.value.pageCount = res.data.pages;
    executingTaskNum.value = res.data.total;
    res.data?.items.forEach((v) => {
      executingTaskData.value.push({
        id: v.id,
        case_id: v.case_id,
        name: v.name,
        milestone_name: v.milestone_name,
        executor_name: v.executor_name,
        start_time: any2standard(v.start_time),
        status: v.status,
        current_step: v.current_step,
        total_step: v.total_step,
        case_expection: v.case_expection,
        case_description: v.case_description,
        case_preset: v.case_preset
      });
    });
  });
};

const finishedTaskPagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1
});
// const finishedTaskSearch = ref('');
const finishedTaskColumns = [
  {
    key: 'case_id',
    title: '编号',
    align: 'center'
  },
  {
    key: 'name',
    title: '名称',
    align: 'center'
  },
  {
    key: 'milestone_name',
    title: '里程碑',
    align: 'center'
  },
  {
    key: 'executor_name',
    title: '执行人',
    align: 'center'
  },
  {
    key: 'end_time',
    title: '结束时间',
    align: 'center'
  },
  {
    key: 'log',
    title: '执行日志',
    align: 'center',
    render: (row) => {
      return h(
        NButton,
        {
          onClick: () => {
            showDrawerCb(row);
            hasFinished.value = true;
          }
        },
        '查看'
      );
    }
  },
  {
    key: 'result',
    title: '执行结果',
    align: 'center',
    render: (row) => {
      if (row.result === 1) {
        return h(
          NIcon,
          {
            color: 'green',
            size: '24',
            style: {
              position: 'relative',
              top: '3px'
            }
          },
          h(CheckCircle, {})
        );
      }
      return h(
        NIcon,
        {
          color: 'rgba(206,64,64,1)',
          size: '26',
          style: {
            position: 'relative',
            top: '1px'
          }
        },
        h(CancelFilled, {})
      );
    }
  },
  {
    key: 'status',
    title: '当前状态',
    align: 'center',
    render: (row) => {
      if (row.result === 1) {
        return h(
          NTag,
          {
            type: 'success',
            round: true
          },
          'Done'
        );
      }
      return h(
        NTag,
        {
          type: 'error',
          round: true
        },
        'Done'
      );
    }
  },
  {
    title: '操作',
    align: 'center',
    render: (row) => {
      return h(
        NSpace,
        {
          justify: 'center',
          align: 'center'
        },
        [
          renderTooltip(
            h(
              NButton,
              {
                size: 'medium',
                type: 'error',
                circle: true,
                onClick: () => {
                  textDialog('warning', '警告', '确认删除手工测试任务？', () => {
                    deleteManualJob(row.id).then(() => {
                      finishedTaskPagination.value.page = 1;
                      getFinishedTask();
                    });
                  });
                }
              },
              h(NIcon, { size: '20' }, h(Delete))
            ),
            '删除'
          )
        ]
      );
    }
  }
];
const finishedTaskData = ref([]);

const finishedTaskPageChange = (page) => {
  finishedTaskPagination.value.page = page;
  getFinishedTask();
};

const changefinishedTaskPagesize = (value) => {
  finishedTaskPagination.value.pageSize = value || 10;
  finishedTaskPagination.value.page = 1;
  getFinishedTask();
};

const getFinishedTask = () => {
  getManualJob({
    status: 1,
    page_num: finishedTaskPagination.value.page,
    page_size: finishedTaskPagination.value.pageSize
  }).then((res) => {
    finishedTaskData.value = [];
    finishedTaskPagination.value.pageCount = res.data.pages;
    finishedTaskNum.value = res.data.total;
    res.data?.items.forEach((v) => {
      finishedTaskData.value.push({
        id: v.id,
        case_id: v.case_id,
        name: v.name,
        milestone_name: v.milestone_name,
        executor_name: v.executor_name,
        start_time: any2standard(v.start_time),
        end_time: any2standard(v.end_time),
        result: v.result,
        status: v.status,
        current_step: v.current_step,
        total_step: v.total_step,
        case_expection: v.case_expection,
        case_description: v.case_description,
        case_preset: v.case_preset
      });
    });
  });
};

const showCaseDrawer = ref(false);
const caseDrawerData = ref({});
const hasFinished = ref(false);

// 获取每一步日志
const getJobLog = (jobId, currentStep) => {
  getManualJobLog(jobId, currentStep).then((res) => {
    commentInput.value = res.data.content || '';
    caseDrawerData.value.operation = res.data.operation;
    expectResult.value = res.data.passed;
  });
};

const expectResult = ref(true);
const showEditor = ref(false);
const commentInput = ref('');
// 富文本配置
const init = {
  language_url: require('@/assets/tinymce/zh_CN.js'), // 中文语言包路径
  language: 'zh_CN',
  skin_url: '/tinymce/skins/ui/oxide', // 编辑器皮肤样式
  content_css: '/tinymce/skins/content/default/content.min.css',
  menubar: false, // 隐藏菜单栏
  height: 600,
  width: '100%',
  toolbar_mode: 'scrolling', // 工具栏模式
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
    reader.onload = function () {
      success(this.result);
    };
  }
};

const editResult = () => {
  showEditor.value = !showEditor.value;
};

const currentStep = ref(0);
const changeSetp = (step) => {
  caseDrawerData.value.current_step = step;
  getJobLog(caseDrawerData.value.id, step);
};

// 关闭日志抽屉回调
const closeDrawerCb = () => {
  showEditor.value = false;
  caseDrawerData.value = {};
  hasFinished.value = false;
  getExecutingTask();
  getFinishedTask();
};

// 退出按钮
const exitDrawer = () => {
  showCaseDrawer.value = false;
};

// 保存按钮
const updateStepLog = () => {
  updateStepLogAxios(caseDrawerData.value.id, {
    step: caseDrawerData.value.current_step,
    content: commentInput.value,
    passed: expectResult.value
  });
};

// 完成执行按钮
const submitStepLog = () => {
  submitManualJob(caseDrawerData.value.id).then(() => {
    showCaseDrawer.value = false;
  });
};

const manualCreateModalRef = ref(null);
const clickCreateJobBtn = () => {
  manualCreateModalRef.value.showModal = true;
};

onMounted(() => {
  getExecutingTask();
  getFinishedTask();
});
</script>

<style lang="less">
.manualContainer {
  display: flex;
  padding: 20px;

  .title {
    font-size: 30px;
    font-weight: 600;
  }

  .secondTitle {
    font-size: 18px;
    display: inline-block;

    .selectNum {
      display: inline-block;
      width: 80px;
    }
  }

  .searchInput {
    width: 100%;
  }

  .anchorWrap {
    width: 144px;
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;

    .anchor {
      z-index: 1;
      position: fixed;
    }

    .createJobBtn {
      position: fixed;
      bottom: 300px;
      color: #cecece;
      cursor: pointer;
      &:hover {
        color: grey;
      }
    }
  }
}

.caseDrawerContainer {
  width: 60% !important;

  .header {
    display: flex;
    align-items: center;

    .backIcon {
      margin-right: 20px;
    }
  }

  .drawer-content {
    .contentWrap {
      padding: 0px 30px;

      .stepWrap {
        margin-top: 20px;
      }

      .commentWrap {
        height: 600px;
        overflow: auto;
      }

      .radioWrap {
        margin-top: 20px;
      }
    }

    .btnWrap {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 100px;

      .btn {
        margin: 0 10px;
      }
    }
  }
}
</style>
