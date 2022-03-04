<template>
  <n-drawer v-model:show="showNewTaskDrawer" width="324px" placement="left">
    <n-drawer-content title="新建任务" closable>
      <n-form
        :model="model"
        :rules="rules"
        ref="formRef"
        label-placement="left"
        :label-width="80"
        size="medium"
      >
        <n-form-item label="名称" path="title">
          <n-input placeholder="请输入任务名称" v-model:value="model.title" />
        </n-form-item>
        <n-form-item label="任务类型" path="type">
          <n-select
            placeholder="请选择"
            :options="taskTypes"
            @update:value="taskTypeChange"
            :value="model.type"
          />
        </n-form-item>
        <n-form-item
          label="执行团队"
          path="group_id"
          v-if="model.type === 'GROUP'"
        >
          <n-select
            placeholder="请选择"
            :options="groups"
            :value="model.group_id"
            :render-label="renderLabel"
            @update:value="getUserByGroup"
            :disabled="model.type == 'PERSON'"
          />
        </n-form-item>
        <n-form-item
          label="执行者"
          path="executor_id"
          v-if="model.type === 'ORGANIZATION' || model.type === 'VERSION'"
        >
          <n-cascader
            :value="model.executor_id"
            placeholder="请选择"
            :options="orgOptions"
            :cascade="false"
            check-strategy="child"
            :show-path="true"
            remote
            @update:value="orgSelect"
            :on-load="handleLoad"
          />
        </n-form-item>
        <n-form-item
          label="执行者"
          path="executor_id"
          v-if="
            model.type !== null &&
              (model.type === 'GROUP' || model.type === 'PERSON') &&
              model.group !== ''
          "
        >
          <n-select
            placeholder="请选择"
            :options="personArray"
            :render-label="renderLabel"
            :disabled="model.type == 'PERSON'"
            v-model:value="model.executor_id"
          />
        </n-form-item>
        <n-form-item label="里程碑" path="milestone_id">
          <n-select
            :options="milestones"
            v-model:value="model.milestone_id"
          ></n-select>
        </n-form-item>
        <n-form-item label="截止日期">
          <n-date-picker   format="yyyy-MM-dd" v-model:value="model.deadline" />
        </n-form-item>
        <n-form-item label="关键词">
          <n-input
            placeholder="请输入关键词"
            v-model:value="model.keywords"
            type="textarea"
          />
        </n-form-item>
        <n-form-item label="摘要">
          <n-input
            placeholder="请输入报告摘要"
            v-model:value="model.abstract"
            type="textarea"
          />
        </n-form-item>
        <n-form-item label="缩略语清单">
          <n-input
            placeholder="请输入缩略语清单"
            v-model:value="model.abbreviation"
            type="textarea"
          />
        </n-form-item>
        <div class="createButtonBox">
          <n-button class="btn" type="error" ghost @click="close"
            >取消</n-button
          >
          <n-button class="btn" type="info" ghost @click="submit">创建</n-button>
        </div>
      </n-form>
    </n-drawer-content>
  </n-drawer>
</template>
<script>
import {
  taskTypes as taskType,
  renderLabel,
  orgOptions,
  handleLoad,
} from '@/views/taskManage/task/modules/createTask';
import { formatTime } from '@/assets/utils/dateFormatUtils';
import { storage } from '@/assets/utils/storageUtils';
export default {
  setup() {
    const taskTypes = [
      ...taskType.value,
      {
        label: '版本任务',
        value: 'VERSION',
      },
    ];
    return {
      orgOptions,
      taskTypes,
      renderLabel,
      handleLoad,
    };
  },
  data() {
    return {
      showNewTaskDrawer: false,
      model: {
        title: '',
        type: '',
        group_id: '',
        executor_id: '',
        deadline: null,
        keywords: '',
        abstract: '',
        abbreviation: '',
        executor_type: '',
      },
      rules: {
        title: {
          trigger: ['input', 'blur'],
          required: true,
          message: '任务名称必填',
        },
        type: {
          trigger: ['change', 'blur'],
          required: true,
          message: '请选择任务类型',
        },
        group_id: {
          trigger: ['change', 'blur'],
          required: true,
          message: '请选择执行团队',
        },
        executor_id: {
          trigger: ['change', 'blur'],
          required: true,
          message: '请选择执行者',
        },
        milestone_id: {
          trigger: ['change', 'blur'],
          required: true,
          message: '请选择里程碑',
        },
      },
      milestones: [],
      personArray: [],
      groups: [],
    };
  },
  mounted() {
    this.getMilestone();
  },
  methods: {
    submit(){
      this.$refs.formRef.validate(error=>{
        if(error){
          window.$message?.error('信息有误，请检查');
        }else {
          this.model.deadline = formatTime(this.model.deadline,'yyyy-MM-dd hh:mm:ss');
          this.$emit('submit',this.model);
          this.close();
        }
      });
    },
    initData() {
      this.model = {
        title: '',
        type: '',
        group_id: '',
        executor_id: '',
        deadline: null,
        keywords: '',
        abstract: '',
        abbreviation: '',
        executor_type: '',
      };
    },
    getMilestone() {
      this.$axios
        .get('/v1/milestone')
        .then((res) => {
          this.milestones = res.map((item) => ({
            label: item.name,
            value: String(item.id),
          }));
        })
        .catch((err) =>
          window.$message?.error(err.data.error_msg || '未知错误')
        );
    },
    orgSelect(value, { type }) {
      this.model.executor_id = value;
      this.model.executor_type = type;
    },
    open() {
      this.showNewTaskDrawer = true;
    },
    close() {
      this.showNewTaskDrawer = false;
      this.initData();
    },
    getUserByGroup(value) {
      this.model.group_id = value;
      this.model.executor_id = '';
      this.personArray = [];
      this.$axios
        .get(`/v1/groups/${this.model.group_id}/users`, {
          page_num: 1,
          page_size: 99999,
          is_admin: true,
        })
        .then((res) => {
          for (const item of res.data.items) {
            this.personArray.push({
              label: item.gitee_name,
              value: String(item.gitee_id),
              avatar_url: item.avatar_url,
            });
          }
        })
        .catch((err) => {
          window.$message?.error(err.data.error_msg || '未知错误');
        });
    },
    getGroup() {
      this.groups = [];
      this.$axios
        .get('/v1/groups', {
          page_num: 1,
          page_size: 99999,
        })
        .then((res) => {
          for (const item of res.data.items) {
            this.groups.push({
              label: item.name,
              value: String(item.id),
              avatar_url: item.avatar_url,
            });
          }
        })
        .catch((err) => {
          window.$message?.error(err.data.error_msg || '未知错误');
        });
    },
    taskTypeChange(value) {
      this.model.type = value;
      this.model.executor_type = 'PERSON';
      if (this.model.type === 'PERSON') {
        this.personArray = [
          {
            label: storage.getValue('gitee_name'),
            value: String(storage.getValue('gitee_id')),
          },
        ];
        this.groups = [{ label: '个人', value: '0' }];
        this.$nextTick(() => {
          this.model.group_id = '0';
          this.model.executor_id = String(storage.getValue('gitee_id'));
        });
      } else {
        this.model.group_id = '';
        this.model.executor_id = '';
      }
      if (this.model.type === 'GROUP') {
        this.getGroup();
      }
    },
  },
};
</script>
