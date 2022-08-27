<template>
  <div>
    <div style="display:flex;align-items:center">
      <template v-for="(item, index) in list" :key="index">
        <n-popover
          placement="top-start"
          trigger="manual" 
          style="box-shadow: none; padding: 0px;"
          :show="handleTipShow(item.key)"
        >
          <template #trigger>
            <n-radio
              @mouseenter="() => { ratioHover = item.key; }"
              @mouseleave="() => { ratioHover = null; }"
              :checked="currentId === item.key"
              :value="item.text"
              size="large"
              name="basic-demo"
              @click="handleClick(item.key)"
              style="--n-radio-size: 26px;"
            />
          </template>
          <div style="display: flex;align-items: center;">
            <span class="step-label">{{ item.text }}</span>
            <n-tooltip v-if="index === list.length - 1 && !done">
              <template #trigger>
                <n-button 
                  v-if="index === list.length - 1  && !done"
                  text 
                  @click="handleRollbackStepClick"
                >
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
      <n-tooltip v-if="!done" :show-arrow="false" trigger="hover">
        <template #trigger>
            <n-icon size="26" :color="hover ? '#4098fc' : ''" @click="addStep" style="cursor: pointer;top: 1px;" @mouseenter="changeHover(true)" @mouseleave="changeHover(false)">
              <ArrowRight20Regular v-if="list.length !== 0" />
              <Play16Filled v-else />
            </n-icon>
        </template>
        {{ addTip }}
      </n-tooltip>
      <div v-if="!done" class="noneline"></div>
      <div v-else class="releaseline" />
      <n-popover 
        trigger="manual" 
        v-if="list.length" 
        :disabled="!done"
        :show="handleTipShow(list[-1]?.key)"
      >
        <template #trigger>
          <n-radio
            :checked="currentId === list[-1]?.key && done"
            size="large"
            name="basic-demo"
            style="--n-radio-size: 26px;margin-right: 17px;"
            :disabled="!done"
            @click="releaseClick"
          />
        </template>
        <div>
          <span class="step-label">{{ list[-1]?.text }}</span><br>
        </div>
      </n-popover>
      <n-icon size="20" style="cursor: pointer;" v-if="list.length">
        <n-popconfirm
          @positive-click="doneEvent"
        >
          <template #trigger>
            <ConnectTarget v-if="!done" />
            <FileDoneOutlined v-else />
          </template>
          确定要{{ done ? '恢复':'结束' }}迭代吗？
        </n-popconfirm>
      </n-icon>
    </div>
  </div>
</template>
<script>
import { toRefs, computed } from 'vue';
import { Play16Filled, ArrowRight20Regular, DeleteArrowBack16Filled } from '@vicons/fluent';
import { ConnectTarget } from '@vicons/carbon';
import { FileDoneOutlined } from '@vicons/antd';
import { modules } from './modules';
export default {
  props: {
    list: Array,
    doneTip: {
      type: String,
      default: '点击后结束迭代测试',
    },
    done: {
      type: Boolean,
      default: false,
    },
    currentId: {
      type: String,
      default: '',
    },
  },
  components: {
    ArrowRight20Regular,
    DeleteArrowBack16Filled,
    FileDoneOutlined,
    ConnectTarget,
    Play16Filled,
  },
  mounted() {
    setTimeout(() => {
      this.tipShow = true;
    }, 300);
  },
  setup(props) {
    const { list } = toRefs(props);
    const addTip = computed(() => {
      if (list.value.length === 5) {
        return '发布';
      } else if (list.value.length !== 0) {
        return '开启下一轮迭代测试';
      }
      return '开启第一轮迭代测试';
    });
    return {
      addTip,
      ...modules,
    };
  },
  data() {
    return {
      hover: false,
      ratioHover: null,
      tipShow: false,
    };
  },
  methods: {
    addStep(){
      this.$emit('add');
    },
    doneEvent(){
      if(!this.done){
        this.$emit('haveDone');
      }else{
        this.$emit('haveRecovery');
      }
    },
    changeHover(show) {
      this.$nextTick(() => {
        this.hover = show;
      });
    },
    releaseClick() {
      this.$emit('release');
    },
    handleClick(milestoneId) {
      this.$emit('stepClick', milestoneId);
    },
    handleRollbackStepClick() {
      this.$emit('rollback');
    },
    handleTipShow(key) {
      if (key === this.currentId && !this.done) {
        return this.tipShow;
      }
      return this.ratioHover === key;
    }
  },
};
</script>
<style lang="less" scoped>
.step-label{
  width: 200px;
  display: inline-block;
}
.elementline{
  color: blue;
}
.divline{
  width: 60%;
  border-bottom: 1.5px solid #303030;
}
.solidline{
  width: 60%;
  border-bottom: 1.5px dashed #303030;
}
.noneline{
  width: 60%;
}
.releaseline{
  width: 60%;
  border-bottom: 1.5px solid #303030;
}
</style>
