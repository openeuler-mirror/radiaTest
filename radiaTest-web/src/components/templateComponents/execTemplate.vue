<template>
  <n-modal v-model:show="showModal" :mask-closable="false">
    <n-card class="modalCard" style="min-width: 680px; max-width: 1280px">
      <n-card
        id="execTemplateCard"
        :title="createTitle('执行模板')"
        size="huge"
        :bordered="false"
        :segmented="{
          content: 'hard'
        }"
        header-style="
            font-size: 20px; 
            height: 40px;
            padding-top: 10px;
            padding-bottom: 10px; 
            font-family: 'v-sans'; 
            background-color: rgba(250,250,252,1);
        "
      >
        <div class="form-box-container">
          <div style="flex: 3">
            <n-form inline :label-width="80" :model="formValue" :rules="rules" size="medium" ref="formRef">
              <n-grid :cols="24">
                <n-form-item-gi :span="23" label="架构" path="frame">
                  <n-select
                    filterable
                    v-model:value="formValue.frame"
                    @update:value="changeFrame"
                    placeholder="请选择架构"
                    :options="[
                      {
                        label: 'aarch64',
                        value: 'aarch64'
                      },
                      {
                        label: 'x86_64',
                        value: 'x86_64'
                      }
                    ]"
                  />
                </n-form-item-gi>
                <n-form-item-gi :span="9" label="机器调度策略" path="select_mode">
                  <n-select
                    :options="[
                      {
                        label: '全自动选取',
                        value: 'auto'
                      },
                      {
                        label: '人工干预',
                        value: 'manual'
                      }
                    ]"
                    style="width: 95%"
                    v-model:value="formValue.select_mode"
                    placeholder="机器调度策略"
                  />
                </n-form-item-gi>
                <n-form-item-gi :span="5" label="是否严格模式" path="strict_mode">
                  <n-switch v-model:value="formValue.strict_mode" :disabled="formValue.select_mode === 'auto'">
                    <template #checked> 是 </template>
                    <template #unchecked> 否 </template>
                  </n-switch>
                </n-form-item-gi>
                <n-form-item-gi :span="9" label="机器组" path="machine_group_id">
                  <n-select
                    :options="machineGroups"
                    v-model:value="formValue.machine_group_id"
                    @update:value="changeFrame"
                    placeholder="请选择"
                  />
                </n-form-item-gi>
                <n-gi :span="24" v-if="formValue.pm_req_num && formValue.select_mode === 'manual'">
                  <n-divider> 物理机选取 </n-divider>
                </n-gi>
                <n-form-item-gi
                  :span="23"
                  label="已选机器"
                  path="machine_list"
                  v-if="formValue.pm_req_num && formValue.select_mode === 'manual'"
                >
                  <selectMachine
                    :text="renderText('pm', formValue.pmachine_list) || '请选择'"
                    @checked="selectmachine('pm', $event)"
                    :data="pmOpt"
                    :checkedMachine="checkedPm"
                    machineType="pm"
                  />
                  {{ formValue.pmachine_list.length }}/{{ formValue.pm_req_num }}
                </n-form-item-gi>
                <n-gi :span="24" v-if="formValue.vm_req_num && formValue.select_mode === 'manual'">
                  <n-divider> 虚拟机选取 </n-divider>
                </n-gi>
                <n-form-item-gi
                  :span="23"
                  label="已选机器"
                  path="machine_list"
                  v-if="formValue.vm_req_num && formValue.select_mode === 'manual'"
                >
                  <selectMachine
                    :text="renderText('vm', formValue.vmachine_list) || '请选择'"
                    @checked="selectmachine('vm', $event)"
                    :data="vmOpt"
                    :checkedMachine="checkedVm"
                    machineType="vm"
                  />
                  {{ formValue.vmachine_list.length }}/{{ formValue.vm_req_num }}
                </n-form-item-gi>
              </n-grid>
            </n-form>
          </div>
          <div style="flex: 2">
            <div class="list-item">
              <div class="list-label">模板名:</div>
              <div class="list-value">{{ formValue?.name }}</div>
            </div>
            <div class="list-item">
              <div class="list-label">描述:</div>
              <div class="list-value">{{ formValue?.description }}</div>
            </div>
            <div class="list-item">
              <div class="list-label">权限归属:</div>
              <div class="list-value">
                {{ formValue?.owner }}
                <n-tag type="success" style="margin-left: 10px">
                  {{ tagOptions[formValue?.template_type] }}
                </n-tag>
              </div>
            </div>
            <div class="list-item">
              <div class="list-label">里程碑:</div>
              <div class="list-value">{{ formValue?.milestone }}</div>
            </div>
            <ExpandedCardTemplate :data="formValue?.cases?.map((item) => ({ name: item.name }))" />
          </div>
        </div>
      </n-card>
      <n-space class="NPbutton">
        <n-button size="large" type="error" @click="onNegativeClick" ghost> 取消 </n-button>
        <n-button size="large" type="primary" @click="postExecData" ghost> 提交 </n-button>
      </n-space>
    </n-card>
  </n-modal>
</template>
<script setup>
import { createTitle } from '@/assets/utils/createTitle';
import ExpandedCardTemplate from '@/components/templateComponents/ExpandedCardTemplate.vue';
import selectMachine from '@/components/machine/selectMachine.vue';
import { implementTemplate } from '@/api/post';
import { getTemplateInfo, getPm, getVm, getMachineGroup } from '@/api/get';
import { unkonwnErrorMsg } from '@/assets/utils/description';

const showModal = ref(false);
const tagOptions = ref({
  person: '个人',
  org: '组织',
  group: '团队'
});

const onNegativeClick = () => {
  showModal.value = false;
};

const machineGroups = ref([]);
function getMachineGroupOptions() {
  getMachineGroup().then((res) => {
    machineGroups.value = res.data.map((item) => ({ label: item.name, value: String(item.id) }));
  });
}
const defaultProp = {
  select_mode: 'auto',
  strict_mode: false,
  vmachine_list: [],
  pmachine_list: []
};
const formValue = ref({ ...defaultProp, machine_group_id: undefined });

const postExecData = () => {
  if (formValue.value.strict_mode) {
    if (
      formValue.value.vmachine_list.length !== formValue.value.vm_req_num ||
      formValue.value.pmachine_list.length !== formValue.value.pm_req_num
    ) {
      window.$message?.error('严格模式下,需要选择相应数量的机器');
      return;
    }
  }

  implementTemplate({
    template_id: formValue.value.id,
    template_name: formValue.value.name,
    frame: formValue.value.frame,
    pmachine_list: formValue.value.pmachine_list,
    vmachine_list: formValue.value.vmachine_list,
    machine_policy: formValue.value.select_mode,
    strict_mode: formValue.value.strict_mode,
    machine_group_id: formValue.value.machine_group_id,
    taskmilestone_id: formValue.value.milestone_id,
    permission_type: formValue.value.git_repo.permission_type,
    creator_id: formValue.value.creator_id,
    org_id: formValue.value.org_id,
    group_id: formValue.value.group_id
  })
    .then((res) => {
      if (res.error_code === '2000') {
        window.$notification?.success({
          content: '测试任务已成功执行',
          meta: `模板：${formValue.value.name}`,
          duration: 2000
        });
        formValue.value.frame = null;
        showModal.value = false;
      }
    })
    .catch((err) => {
      if (!err.message && !err.data.validation_error) {
        window.$message?.error('发生未知错误，执行失败，请联系管理员进行处理');
      } else if (err.data.validation_error) {
        window.$message?.error(err.data.validation_error.body_params[0].msg);
      } else {
        window.$message?.error(err.message);
      }
      formValue.value.frame = null;
    });
};

const pmOpt = ref();
const vmOpt = ref();

const renderExecute = (row) => {
  getTemplateInfo(row.id).then((res) => {
    formValue.value = { ...res.data, ...row, ...defaultProp };
  });
  getMachineGroupOptions();
};

const checkedVm = ref([]);
const checkedPm = ref([]);

function selectmachine(type, value) {
  if (type === 'pm') {
    if (formValue.value.strict_mode && formValue.value.pm_req_num < value.length) {
      window.$message?.error('严格模式下,需要选择相应数量的机器');
      return;
    }
    checkedPm.value = value;
    formValue.value.pmachine_list = value;
  } else {
    if (formValue.value.strict_mode && formValue.value.vm_req_num < value.length) {
      window.$message?.error('严格模式下,需要选择相应数量的机器');
      return;
    }
    checkedVm.value = value;
    formValue.value.vmachine_list = value;
  }
}

async function changeFrame() {
  try {
    if (formValue.value.frame && formValue.value.machine_group_id) {
      const data = await getPm({
        frame: formValue.value.frame,
        machine_purpose: 'run_job',
        machine_group_id: formValue.value.machine_group_id
      });
      pmOpt.value = data.data;
      checkedVm.value = [];
      checkedPm.value = [];
      formValue.value.pmachine_list = [];
      formValue.value.vmachine_list = [];
      const vmdata = await getVm({
        frame: formValue.value.frame,
        machine_purpose: 'run_job',
        machine_group_id: formValue.value.machine_group_id
      });
      vmOpt.value = vmdata.data;
    }
  } catch (error) {
    window.$message?.error(error.data?.error_msg || error.message || unkonwnErrorMsg);
  }
}

function renderText(type, values) {
  const result = [];
  if (values.length) {
    values.forEach((item) => {
      const element = type === 'vm' ? vmOpt.value.find((i) => i.id === item) : pmOpt.value.find((i) => i.id === item);
      result.push(element?.ip);
    });
    return result.join(',');
  }
  return '';
}

const rules = {
  machine_group_id: {
    required: true,
    message: '请选择机器组',
    trigger: ['blur']
  },
  frame: {
    required: true,
    message: '请选择架构',
    trigger: ['blur']
  }
};

defineExpose({
  showModal,
  renderExecute
});
</script>

<style lang="less" scoped>
.form-box-container {
  display: flex;
  .list-item {
    display: flex;
    margin: 15px 10px;
    align-items: center;
    .list-label {
      width: 80px;
      flex-shrink: 0;
      font-weight: 500;
    }
    .list-value {
      width: 100%;
    }
  }
}
</style>
