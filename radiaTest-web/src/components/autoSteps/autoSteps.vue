<template>
  <div>
    <div style="display:flex;align-items:center">
      <template v-for="(item, index) in list" :key="index">
        <n-popover trigger="hover">
          <template #trigger>
            <n-radio
              :checked="currentId === item.key"
              :value="item.text"
              size="large"
              name="basic-demo"
              @click="handleClick(item.key)"
              style="--n-radio-size: 26px;"
            />
          </template>
          <div>
            <span class="step-label">{{ item.text }}</span><br>
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
      <n-radio
        :checked="releaseRef"
        size="large"
        name="basic-demo"
        style="--n-radio-size: 26px;margin-right: 17px;"
        :disabled="!done"
        v-if="iterating"
        @click="releaseClick"
      />
      <n-icon size="20" style="cursor: pointer;" v-if="list.length">
        <n-popconfirm
          @positive-click="doneEvent"
          @negative-click="handleNegativeClick"
        >
          <template #trigger>
            <ConnectTarget v-if="!done" />
            <ConnectSource v-else />
          </template>
          确定要{{ done ? '恢复':'结束' }}迭代吗？
        </n-popconfirm>
      </n-icon>
    </div>
  </div>
</template>
<script>
import { toRefs, computed } from 'vue';
import { Play16Filled, ArrowRight20Regular } from '@vicons/fluent';
import { ConnectSource, ConnectTarget } from '@vicons/carbon';
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
    ConnectSource,
    ConnectTarget,
    Play16Filled,
  },
  watch: {
    done: {
      handler(val) {
        this.$nextTick(()=>{
          if (val) {
            this.releaseRef = true;
          } else {
            this.releaseRef = false;
          }
        });
      },
      deep: true,
    },
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
    };
  },
  methods: {
    addStep(){
      this.$emit('add');
    },
    doneEvent(){
      if(!this.done){
        this.releaseRef = true;
        this.$emit('haveDone');
        window.$message.success('已结束迭代!');
      }else{
        this.releaseRef = false;
        this.$emit('haveRecovery');
        window.$message.success('已恢复迭代!');
      }
    },
    changeHover(show) {
      this.$nextTick(() => {
        this.hover = show;
      });
    },
    releaseClick() {
      this.releaseRef = true;
      this.$emit('releaseclick');
    },
    handleClick(milestoneId) {
      this.releaseRef = false;
      this.$emit('stepClick', milestoneId);
    },
    handleNegativeClick() {
      window.$message.info('取消操作!');
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
