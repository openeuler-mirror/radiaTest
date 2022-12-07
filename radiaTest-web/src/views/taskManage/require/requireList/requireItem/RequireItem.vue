<template>
  <div class="translate-box">
    <div class="require-item" @click="handleItemClick">
      <div class="require-item-header">
        <p class="title">{{ props.item.title }}</p>
        <div class="subtitle">
          <p class="info">
            影响力价值:
            <span class="var">{{ props.item.total_reward }}</span>
            <n-icon>
              <radio />
            </n-icon>
          </p>
          <p class="info">
            状态:
            <span class="var">{{ statusDict[props.item.status] }}</span>
          </p>
        </div>
      </div>
      <div class="require-item-body">
        <pre class="content">{{ props.item.remark }}</pre>
      </div>
      <div class="require-item-footer">
        <p class="info">
          发布人:
          <span class="var">
            {{ props.item.publisher.name ? props.item.publisher.name : props.item.publisher.gitee_name }}
          </span>
        </p>
        <p class="info">
          发布时间:
          <span class="var">{{ props.item.create_time }}</span>
        </p>
      </div>
    </div>
    <div class="button-container">
      <n-tooltip trigger="hover">
        <template #trigger>
          <div class="detail button" @click="() => { showDetailModal = true; }">
            <n-icon :size="24">
              <md-more />
            </n-icon>
          </div>
        </template>
        查看详情
      </n-tooltip>
      <n-tooltip 
        trigger="hover"
        v-if="
          props.item.status === 'idle' 
          && props.item.publisher.gitee_id.toString() === storage.getValue('gitee_id')
        " 
      >
        <template #trigger>
          <div class="reject button" @click="handleDeleteRequire">
            <n-icon :size="24" color="red">
              <DeleteFilled />
            </n-icon>
          </div>
        </template>
        删除需求
      </n-tooltip>
      <n-tooltip 
        trigger="hover"
        v-if="
          props.item.status === 'idle' 
          && props.item.publisher.gitee_id.toString() !== storage.getValue('gitee_id')
        " 
      >
        <template #trigger>
          <div class="accept button" @click="handleAcceptRequire">
            <n-icon :size="24" color="#ffc227">
              <Archive />
            </n-icon>
          </div>
        </template>
        接受需求
      </n-tooltip>
      <n-tooltip 
        trigger="hover"
        v-if="
          props.item.status === 'accepted' 
          && props.item.acceptor.gitee_id.toString() === storage.getValue('gitee_id')
        " 
      >
        <template #trigger>
          <div class="reject button" @click="handleRejectRequire">
            <n-icon :size="24" color="red">
              <Close />
            </n-icon>
          </div>
        </template>
        放弃需求
      </n-tooltip>
      <n-tooltip 
        trigger="hover"
        v-if="
          props.item.status === 'accepted' 
          && props.item.publisher.gitee_id.toString() === storage.getValue('gitee_id')
        " 
      >
        <template #trigger>
          <div class="complete button" @click="handleValidateRequire">
            <n-icon :size="24" color="#18A058">
              <md-checkmark-circle />
            </n-icon>
          </div>
        </template>
        验收通过
      </n-tooltip>
      <n-tooltip 
        trigger="hover"
        v-if="
          props.item.status === 'validated' 
          && props.item.acceptor.gitee_id.toString() === storage.getValue('gitee_id')
          && props.item.dividable_reward > 0
        " 
      >
        <template #trigger>
          <div class="divide button" @click="handleDivideRewards">
            <n-icon :size="24" color="#4b94d5">
              <radio />
            </n-icon>
          </div>
        </template>
        影响力分配
      </n-tooltip>
    </div>
  </div>
  <n-modal v-model:show="showDetailModal">
    <require-item-detail 
      :item="props.item"
      @close="() => { showDetailModal = false; }"
    />
  </n-modal>
  <n-modal v-model:show="showDeleteModal">
    <n-dialog
      type="warning"
      title="删除需求"
      negative-text="取消"
      positive-text="确认"
      @positive-click="deleteSubmitCallback"
      @negative-click="deleteCancelCallback"
      @close="deleteCancelCallback"
    >
      <p class="dialog-content">{{ `是否确认删除&lt;${props.item.title}&gt;?` }}</p>
    </n-dialog>
  </n-modal>
  <n-modal v-model:show="showAcceptModal">
    <n-dialog
      type="info"
      title="接受需求"
      negative-text="取消"
      positive-text="确认"
      @positive-click="acceptSubmitCallback"
      @negative-click="acceptCancelCallback"
      @close="acceptCancelCallback"
    >
      <p class="dialog-content">{{ `是否接受&lt;${props.item.title}&gt;?` }}</p>
      <p class="dialog-tip tip-info">{{ '注意：无法顺利通过验收将影响接受方信誉分' }}</p>
      <n-form ref="acceptFormRef" :model="acceptForm" :rules="acceptRules">
        <n-form-item>
          <n-cascader
            v-model:value="acceptForm.acceptor_group_id"
            placeholder="请选择需求接受方"
            :options="typeOptions"
            check-strategy="child"
            remote
            :on-load="handleLoad"
            @update:value="handleAcceptorUpdate"
          />
        </n-form-item>
      </n-form>
    </n-dialog>
  </n-modal>
  <n-modal v-model:show="showRejectModal">
    <n-dialog
      type="warning"
      title="放弃需求"
      negative-text="取消"
      positive-text="确认"
      @positive-click="rejectSubmitCallback"
      @negative-click="rejectCancelCallback"
      @close="rejectCancelCallback"
    >
      <p class="dialog-content">{{ `是否确认放弃&lt;${props.item.title}&gt;?` }}</p>
      <p class="dialog-tip tip-warning">{{ '警告：验收前中途放弃需求会导致信誉分下降，请谨慎放弃' }}</p>
    </n-dialog>
  </n-modal>
  <n-modal v-model:show="showValidateModal">
    <n-dialog
      type="success"
      title="验收需求"
      negative-text="取消"
      positive-text="确认"
      @positive-click="validateSubmitCallback"
      @negative-click="validateCancelCallback"
      @close="validateCancelCallback"
    >
      <p class="dialog-content">{{ `是否确认对&lt;${props.item.title}&gt;所有交付件的验收?` }}</p>
      <p class="dialog-tip tip-info">{{ '注意：确认后将锁定交付件列表，并解锁该需求的可分配奖励，此过程不可逆' }}</p>
    </n-dialog>
  </n-modal>
  <n-modal v-model:show="showDivideModal">
    <n-dialog
      style="width: 800px;"
      type="info"
      title="贡献者奖励分配"
      negative-text="取消"
      positive-text="确认"
      @positive-click="divideSubmitCallback"
      @negative-click="divideCancelCallback"
      @close="divideCancelCallback"
    >
      <p class="dialog-content">{{ `以下列方案分配剩余的影响力奖励` }}</p>
      <p class="dialog-tip tip-info">{{ '注意：剩余奖励归零前，支持多次有效分配（团队影响力自动增加，无需分配）' }}</p>
      <div class="dividable-reward-container">
        <n-progress 
          type="line" 
          :percentage="rewardsPercentage"
        >
          {{ props.item.dividable_reward - sumDivideRewards }}
        </n-progress>
      </div>
      <div 
        class="require-attributor-container" 
        v-for="(attributor, index) in requireAttributors"
        :key="index"
      >
        <div>
          {{ attributor.user_name }}
        </div>
        <div class="reward-slider">
          <n-slider
            v-model:value="attributor.reward"
            :max="props.item.dividable_reward"
            @update:value="handleAttributorRewardUpdate(index)"
          >
            <template #thumb>
              <n-icon-wrapper :size="24" :border-radius="12">
                <n-icon :size="18" :component="Radio" />
              </n-icon-wrapper>
            </template>
          </n-slider>
        </div>
        <div>
          {{ attributor.reward }}
        </div>
      </div>
    </n-dialog>
  </n-modal>
</template>

<script setup>
import { useMessage } from 'naive-ui';
import { storage } from '@/assets/utils/storageUtils';
import { DeleteFilled } from '@vicons/material';
import { Radio, Archive, Close } from '@vicons/ionicons5';
import { MdMore, MdCheckmarkCircle } from '@vicons/ionicons4';
import RequireItemDetail from './requireItemDetail/RequireItemDetail';
import { getGroup, getRequireAttributors } from '@/api/get';
import { deleteRequire } from '@/api/delete';
import { 
  personAcceptRequire, 
  groupAcceptRequire, 
  rejectRequire ,
  validateRequire,
} from '@/api/put';
import { divideRequireRewards } from '@/api/post';

const props = defineProps({
  item: Object
});
const emit = defineEmits(['item-click']);

const message = useMessage();

const statusDict = {
  idle: '可接受',
  accepted: '已接受',
  validated: '已验收',
};

function handleItemClick() {
  emit('item-click');
}

const acceptFormRef = ref(null);
const acceptRules = ref({});
const acceptForm = ref({
  acceptor_type: 'person',
  acceptor_group_id: null,
  acceptor_group_name: null,
});

const typeOptions = ref([
  { label: '团队', value: 'group', isLeaf: false },
  { label: '个人', value: 'person', isLeaf: true }
]);
function handleLoad(option) {
  return new Promise((resolve, reject) => {
    getGroup({ page_num: 1, page_size: 99999 })
      .then((res) => {
        option.children = res.data.items.map((item) => ({
          label: item.name,
          value: item.id,
        }));
        resolve();
      })
      .catch((err) => reject(err));
  });
}
function handleAcceptorUpdate(value, option) {
  if (value !== 'person' && typeof(value) === 'number') {
    acceptForm.value.acceptor_type = 'group';
    acceptForm.value.acceptor_group_name = option.label;
  }
}

const requireAttributors = ref([]);

const showDetailModal = ref(false);
const showDeleteModal = ref(false);
const showAcceptModal = ref(false);
const showRejectModal = ref(false);
const showValidateModal = ref(false);
const showDivideModal = ref(false);

function handleAcceptRequire() {
  showAcceptModal.value = true;
}
function acceptSubmitCallback() {
  if ( acceptForm.value.acceptor_type === 'person' ) {
    personAcceptRequire(props.item.id)
      .then(() => {
        message.success(`你已接受<${props.item.title}>`);
      })
      .finally(() => {
        showAcceptModal.value = false;
        acceptForm.value = {
          acceptor_type: 'person',
          acceptor_group_id: null,
          acceptor_group_name: null,
        };
      });
  } else {
    groupAcceptRequire(props.item.id, acceptForm.value.acceptor_group_id)
      .then(() => {
        message.success(
          `团队${acceptForm.value.acceptor_group_name}已接受<${props.item.title}>`
        );
      })
      .finally(() => {
        showAcceptModal.value = false;
        acceptForm.value = {
          acceptor_type: 'person',
          acceptor_group_id: null,
          acceptor_group_name: null,
        };
      });
  }
}
function acceptCancelCallback() {
  showAcceptModal.value = false;
  acceptForm.value = {
    acceptor_type: 'person',
    acceptor_group_id: null,
    acceptor_group_name: null,
  };
}

function handleDeleteRequire() {
  showDeleteModal.value = true;
}
function deleteCancelCallback() {
  showDeleteModal.value = false;
}
function deleteSubmitCallback() {
  deleteRequire(props.item.id)
    .then(() => {
      message.success(`需求${props.item.title}已删除`);
    })
    .finally(() => {
      showDeleteModal.value = false;
    });
}

function handleRejectRequire() {
  showRejectModal.value = true;
}
function rejectSubmitCallback() {
  rejectRequire(props.item.id)
    .then((res) => {
      message.success(`已放弃<${props.item.title}>，信誉分减少${res.data}`);
    })
    .finally(() => {
      showRejectModal.value = false;
    });
}
function rejectCancelCallback() {
  showRejectModal.value = false;
}

function handleValidateRequire() {
  showValidateModal.value = true;
}
function validateSubmitCallback() {
  validateRequire(props.item.id)
    .then(() => {
      message.success(`已通过对<${props.item.title}>的验收，此需求已锁定`);
    })
    .finally(() => {
      showValidateModal.value = false;
    });
}
function validateCancelCallback() {
  showValidateModal.value = false;
}

function handleDivideRewards() {
  showDivideModal.value = true;
  getRequireAttributors(props.item.id)
    .then((res) => {
      requireAttributors.value = res.data.map((item) => {
        return {
          user_id: item.gitee_id,
          user_name: item.gitee_name,
          reward: 0,
        };
      });
    });
}
function divideSubmitCallback() {
  divideRequireRewards(props.item.id, { strategies: requireAttributors.value })
    .then((res) => {
      message.success(`分配成功，剩余可分配奖励${res.data}`);
    })
    .finally(() => {
      showDivideModal.value = false;
    });
}
function divideCancelCallback() {
  showDivideModal.value = false;
}

function renderContainers() {
  const elements = document.getElementsByClassName('require-item-container');
  elements.forEach((el) => {
    const [buttonContainer] = el.getElementsByClassName('button-container');
    buttonContainer.style.right = `-${buttonContainer.childElementCount * 50}px`;
    el.style.width = `calc(100% + ${buttonContainer.childElementCount * 50}px)`;
  });
}

const sumDivideRewards = computed(() => {
  const _rewards = [...requireAttributors.value.map(item => item.reward)];
  if (_rewards.length > 0) {
    return _rewards.reduce((x, y) => x + y);
  }
  return 0;
});

const rewardsPercentage = computed(() => {
  const result = Math.round(
    ( props.item.dividable_reward - sumDivideRewards.value ) / props.item.total_reward * 100
  );
  return result;
});

function handleAttributorRewardUpdate(index) {
  const diff = props.item.dividable_reward - sumDivideRewards.value;
  if (diff < 0) {
    requireAttributors.value[index].reward = requireAttributors.value[index].reward + diff;
  }
}

onMounted(() => {
  renderContainers();
});
</script>

<style scoped lang="less">
.translate-box {
  display: flex;
  .require-item {
    width: 100%;
    .require-item-header {
      display: flex;
      justify-content: space-between;
      .title {
        padding: 0 20px;
        color: #002FA7;
        font-size: 20px;
        font-weight: 900;
      }
      .subtitle {
        display: flex;
        justify-content: flex-end;
        .info {
          display: flex;
          align-items: center;
          font-size: 14px;
          padding: 10px 20px;
        }
      }
    }
    .require-item-body {
      .content {
        padding: 0 20px;
        color: grey;
        font-size: 14px;
      }
    }
    .require-item-footer {
      display: flex;
      justify-content: flex-end;
      .info {
        font-size: 14px;
        padding: 0 20px;
      }
    }
  }
}
.var {
  padding-right: 5px;
  padding-left: 10px;
  color: #59a9ee;
}
.button-container {
  display: flex;
  align-items: center;
  .button {
    width: 50px;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .button:hover {
    box-shadow: 0 1px 2px -2px rgba(0, 0, 0, 0.08), 0 3px 6px 0 rgba(0, 0, 0, 0.06), 0 5px 12px 4px rgba(0, 0, 0, 0.04)
  }
  .accept {
    background-color: #fffaf0;
  }
  .complete {
    background-color: #d8f3e5;
  }
  .reject {
    background-color: #ffe3e3;
  }
  .detail {
    background-color: #f5f5f5;
  }
  .divide {
    background-color: #d1f1ff;
  }
}
.dialog-content {
  font-size: 18px;
  font-weight: 500;
}
.dialog-tip {
  font-size: 12px;
}
.tip-warning {
  color: #de5656;
}
.tip-info {
  color: grey;
}
.dividable-reward-container {
  margin-bottom: 20px;
}
.require-attributor-container {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
}
.reward-slider {
  width: 80%;
  margin: 0 20px 0 20px;
}
</style>
