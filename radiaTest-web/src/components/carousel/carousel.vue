<template>
  <div class="carousel" @mouseenter="stopFN" @mouseleave="continueFN">
    <ul class="carousel-body">
      <!-- 轮播的图片 -->
      <li
        v-for="(item, i) in sliders"
        :key="item.id"
        class="carousel-item"
        :class="{ fade: i === index }"
      >
        <slot :name="`imgTop-${i}`"></slot>
        <img :src="item.imgUrl" alt="" class="carousel-img" />
        <slot :name="`imgButtom-${i}`"></slot>
      </li>
    </ul>

    <!-- 左侧上一页点击按钮 -->
    <!-- <a @click="toggleFN(-1)" href="javascript:;" class="carousel-btn prev"
      ><i class="iconfont icon-angle-left"></i
    ></a> -->

    <!-- 右侧下一页点击按钮 -->
    <!-- <a @click="toggleFN(1)" href="javascript:;" class="carousel-btn next"
      ><i class="iconfont icon-angle-right"></i
    ></a> -->

    <!-- 导航条区域 -->
    <!-- <div class="carousel-indicator">
      <span
        v-for="i in sliders.length"
        :key="i"
        :class="{ active: index === i - 1 }"
        @click="index = i - 1"
      ></span>
    </div> -->
  </div>
</template>

<script>
import { ref, onUnmounted } from 'vue';

export default {
  name: 'Carousel',
  props: {
    sliders: {
      type: Array,
      default: () => [],
    },
    duration: {
      type: Number,
      default: 1,
    },
    autoplay: {
      type: Boolean,
      default: false,
    },
    mouseStop: {
      type: Boolean,
      default: true
    }
  },
  watch: {
    sliders: {
      handler() {
        if (this.sliders.length > 1 && this.autoplay) {
          this.index = 0;
          this.autoplayFN();
        }
      },
      immediate: true,
    },
  },
  setup(props, { emit }) {
    const index = ref(0);
    const timer = ref(null);
    const autoplayFN = () => {
      clearInterval(timer.value);
      timer.value = setInterval(() => {
        index.value++;
        emit('change', index);
        if (index.value >= props.sliders.length) {
          index.value = 0;
        }
      }, props.duration);
    };

    const stopFN = () => {
      if (props.mouseStop && timer.value) {
        clearInterval(timer.value);
      }
    };
    const continueFN = () => {
      if (props.sliders.length > 1 && props.autoplay) {
        autoplayFN();
      }
    };

    function toggleFN(num) {
      index.value += num;
      if (index.value >= props.sliders.length) {
        index.value = 0;
      }
      if (index.value < 0) {
        index.value = props.sliders.length - 1;
      }
    }

    onUnmounted(() => {
      if (timer.value) {
        clearInterval(timer.value);
      }
    });

    return { index, stopFN, continueFN, toggleFN, autoplayFN };
  },
};
</script>
<style scoped lang="less">
.carousel {
  width: 100%;
  height: 100%;
  min-width: 300px;
  min-height: 150px;
  position: relative;
  .carousel {
    &-body {
      width: 100%;
      height: 100%;
      overflow: hidden;
      margin: 0;
      padding: 0;
    }
    &-item {
      width: 100%;
      height: 100%;
      position: absolute;
      display: flex;
      flex-direction: column;
      left: 0;
      top: 0;
      opacity: 0;
      transition: all 0.1s linear;
      list-style: none;
      &.fade {
        animation: fadeInUp;
        opacity: 1;
        animation-duration: 0.5s;
      }
      img {
        width: 100%;
        height: 100%;
        object-fit: fill;
        overflow: hidden;
      }
    }
    &-indicator {
      position: absolute;
      left: 0;
      bottom: 20px;
      z-index: 2;
      width: 100%;
      text-align: center;
      span {
        display: inline-block;
        width: 12px;
        height: 12px;
        background: rgba(0, 0, 0, 0.2);
        border-radius: 50%;
        cursor: pointer;
        ~ span {
          margin-left: 12px;
        }
        &.active {
          background: #fff;
        }
      }
    }
    &-btn {
      width: 44px;
      height: 44px;
      background: rgba(0, 0, 0, 0.2);
      color: #fff;
      border-radius: 50%;
      position: absolute;
      top: 228px;
      z-index: 2;
      text-align: center;
      line-height: 44px;
      opacity: 0;
      transition: all 0.5s;
      &.prev {
        left: 20px;
      }
      &.next {
        right: 20px;
      }
    }
  }
  &:hover {
    .carousel-btn {
      opacity: 1;
    }
  }
}
</style>
