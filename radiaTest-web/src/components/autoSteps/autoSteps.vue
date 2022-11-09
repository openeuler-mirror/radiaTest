<template>
  <div>
    <div style="display: flex; align-items: center">
      <template v-for="(item, index) in list" :key="index">
        <n-popover
          placement="top-start"
          trigger="manual"
          style="box-shadow: none; padding: 0px"
          :show="handleTipShow(item.id)"
        >
          <template #trigger>
            <n-radio
              @mouseenter="
                () => {
                  ratioHover = item.id;
                }
              "
              @mouseleave="
                () => {
                  ratioHover = null;
                }
              "
              :checked="currentId === item.id"
              :value="item.name"
              size="large"
              name="basic-demo"
              @click="handleClick(item)"
              style="--n-radio-size: 26px"
            />
          </template>
          <div style="display: flex; align-items: center">
            <span class="step-label">{{ item.name }}</span>
            <n-tooltip>
              <template #trigger>
                <n-button type="primary" class="step-button" :bordered="false" text @click="handleChecklistBoard">
                  <n-icon :size="18">
                    <ChecklistFilled />
                  </n-icon>
                </n-button>
              </template>
              CheckList
            </n-tooltip>
            <n-tooltip>
              <template #trigger>
                <n-button type="primary" class="step-button" :bordered="false" text @click="handleMilestone">
                  <n-icon :size="18">
                    <Milestone />
                  </n-icon>
                </n-button>
              </template>
              Milestone
            </n-tooltip>
            <n-tooltip v-if="index === list.length - 1 && !done">
              <template #trigger>
                <n-button class="step-button" :bordered="false" text @click="handleRollbackStepClick">
                  <n-icon :size="18">
                    <DeleteArrowBack16Filled />
                  </n-icon>
                </n-button>
              </template>
              回退至上一迭代
            </n-tooltip>
          </div>
        </n-popover>
        <div class="divline" v-if="index !== list.length - 1"></div>
      </template>
      <div v-if="list.length !== 0 && !done" class="solidline" style=""></div>
      <!-- 转测图标 -->
      <n-tooltip v-if="!done" :show-arrow="false" trigger="hover">
        <template #trigger>
          <n-icon
            size="26"
            :color="hover ? '#4098fc' : ''"
            @click="addStep"
            style="cursor: pointer; top: 1px"
            @mouseenter="changeHover(true)"
            @mouseleave="changeHover(false)"
          >
            <ArrowRight20Regular v-if="list.length !== 0" />
            <Play16Filled v-else />
          </n-icon>
        </template>
        {{ addTip }}
      </n-tooltip>
      <div v-if="!done" class="noneline"></div>
      <div v-else class="releaseline" />
      <n-popover trigger="manual" v-if="list.length" :show="handleTipShow(list[-1]?.id)">
        <template #trigger>
          <n-radio
            v-show="!done"
            size="large"
            name="basic-demo"
            style="--n-radio-size: 26px; margin-right: 17px"
            :disabled="!done"
          />
        </template>
        <div>
          <span class="step-label">{{ list[-1]?.name }}</span
          ><br />
        </div>
      </n-popover>
      <!-- 发布或回退 -->
      <n-icon size="20" style="cursor: pointer" v-if="list.length">
        <n-popconfirm @positive-click="doneEvent">
          <template #trigger>
            <ConnectTarget v-if="!done" />
            <FileDoneOutlined v-else />
          </template>
          {{ !done ? `发布` : '取消发布，恢复至最后一轮迭代' }}
        </n-popconfirm>
      </n-icon>
    </div>
  </div>
</template>
<script>
import { toRefs, computed } from 'vue';
import { Play16Filled, ArrowRight20Regular, DeleteArrowBack16Filled } from '@vicons/fluent';
import { ConnectTarget, Milestone } from '@vicons/carbon';
import { FileDoneOutlined } from '@vicons/antd';
import { ChecklistFilled } from '@vicons/material';
import { modules } from './modules';
export default {
  props: {
    list: Array,
    doneTip: {
      type: String,
      default: '点击后结束迭代测试'
    },
    done: {
      type: Boolean,
      default: false
    },
    currentId: {
      type: String,
      default: ''
    },
    hasQualityboard: {
      type: Boolean,
      default: false
    }
  },
  components: {
    ArrowRight20Regular,
    DeleteArrowBack16Filled,
    FileDoneOutlined,
    ConnectTarget,
    Play16Filled,
    ChecklistFilled,
    Milestone
  },
  setup(props) {
    const { list, hasQualityboard } = toRefs(props);
    const addTip = computed(() => {
      if (!hasQualityboard.value) {
        return '创建qualityboard';
      } else if (list.value.length !== 0) {
        return '开启下一轮迭代测试';
      }
      return '开启第一轮迭代测试';
    });
    return {
      addTip,
      ...modules
    };
  },
  data() {
    return {
      hover: false,
      ratioHover: null
    };
  },
  methods: {
    addStep() {
      this.$emit('add');
    },
    doneEvent() {
      if (!this.done) {
        this.$emit('haveDone');
      } else {
        this.$emit('haveRecovery');
      }
    },
    changeHover(show) {
      this.$nextTick(() => {
        this.hover = show;
      });
    },
    handleClick(item) {
      this.$emit('stepClick', item);
    },
    handleRollbackStepClick() {
      this.$emit('rollback');
    },
    handleTipShow(key) {
      if (key === this.currentId || this.ratioHover === key) {
        return true;
      }
      return false;
    },
    handleChecklistBoard() {
      this.$emit('handleChecklistBoard');
    },
    handleMilestone() {
      this.$emit('handleMilestone');
    }
  }
};
</script>
<style lang="less" scoped>
.step-label {
  width: auto;
  display: inline-block;
}
.step-button {
  margin: 0 5px;
}
.elementline {
  color: blue;
}
.divline {
  width: 60%;
  border-bottom: 1.5px solid #303030;
}
.solidline {
  width: 60%;
  border-bottom: 1.5px dashed #303030;
}
.noneline {
  width: 60%;
}
.releaseline {
  width: 50px;
}
</style>
