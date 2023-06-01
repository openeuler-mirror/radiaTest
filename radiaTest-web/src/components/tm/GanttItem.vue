<template>
  <div
    class="ganttitem-container"
    :style="{
      background: bgColor,
      left: currentPosition + 'px',
      top: positionTop + 'px',
      width: currentWidth + 'px'
    }"
    @click="jumpToDetail"
  >
    <div class="item-wrap">
      <div class="bar" :style="{ width: barWidth + 'px' }"></div>
      <div class="items-row-item-label">
        <div class="item-icon" v-show="showLeftArror">
          <n-icon :size="18" color="white">
            <ArrowBigLeft />
          </n-icon>
        </div>
        <div class="item-image">
          <n-avatar :size="34" round :src="options.url" />
        </div>
        <div class="item-text">
          <div class="item-label">{{ options.name }}</div>
          <div class="item-description">{{ options.description }}</div>
        </div>
        <div class="item-icon" v-show="showRightArror">
          <n-icon :size="18" color="white">
            <ArrowBigRight />
          </n-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import dayjs from 'dayjs';
import { ArrowBigLeft, ArrowBigRight } from '@vicons/tabler';
import { getDetail } from '@/views/taskManage/task/modules/taskDetail.js';

const props = defineProps([
  'options',
  'dateRange',
  'totalDays',
  'totalMonths',
  'zoomValue',
  'startDateCalendar',
  'endDateCalendar',
  'scrollLeft'
]);
const { options, dateRange, totalDays, totalMonths, zoomValue, startDateCalendar, endDateCalendar, scrollLeft } =
  toRefs(props);
const positionLeft = ref(0); // 左偏移
const positionTop = ref(0); // 上偏移
const itemWidth = ref(0); // 宽度
const barWidth = ref(0); // 完成度百分比宽度
const showLeftArror = ref(false); // 显示左箭头
const showRightArror = ref(false); // 显示右箭头
const startDate = dayjs(options.value.start_time); // 任务开始日期
const endDate = dayjs(options.value.end_time); // 任务结束日期

// 按月显示
// eslint-disable-next-line complexity
const initMonth = () => {
  let startMonth = startDate.diff(startDateCalendar.value, 'month'); // 任务开始位置
  let endMonth = endDate.diff(startDateCalendar.value, 'month'); // 任务结束位置
  let startDatePosition = startDate.date() / startDate.daysInMonth();
  let endDatePosition = endDate.date() / endDate.daysInMonth();

  if (
    (startDate.isBefore(startDateCalendar.value) && endDate.isBefore(startDateCalendar.value)) ||
    (startDate.isAfter(endDateCalendar.value) && endDate.isAfter(endDateCalendar.value))
  ) {
    itemWidth.value = 0;
    showLeftArror.value = false;
    showRightArror.value = false;
  } else if (startDate.isBefore(startDateCalendar.value) && !endDate.isAfter(endDateCalendar.value)) {
    showLeftArror.value = true;
    showRightArror.value = false;
    startMonth = 0;
    itemWidth.value = (endMonth - startMonth + endDatePosition) * 80;
    positionLeft.value = 0;
  } else if (startDate.isBefore(startDateCalendar.value) && endDate.isAfter(endDateCalendar.value)) {
    showLeftArror.value = true;
    showRightArror.value = true;
    startMonth = 0;
    itemWidth.value = totalMonths.value * 80;
    positionLeft.value = 0;
  } else if (!startDate.isBefore(startDateCalendar.value) && endDate.isAfter(endDateCalendar.value)) {
    showLeftArror.value = false;
    showRightArror.value = true;
    itemWidth.value = (totalMonths.value - startMonth - startDatePosition) * 80;
    positionLeft.value = (startMonth + startDatePosition) * 80;
  } else {
    showLeftArror.value = false;
    showRightArror.value = false;
    itemWidth.value = (endMonth - startMonth - startDatePosition + endDatePosition) * 80;
    positionLeft.value = (startMonth + startDatePosition) * 80;
  }
  positionTop.value = (options.value.heightLine - 1) * 72 + 11;
  barWidth.value = itemWidth.value * (options.value.percentage / 100);
};

// 按日显示
// eslint-disable-next-line complexity
const initDay = () => {
  let startDay = startDate.diff(startDateCalendar.value, 'day'); // 任务开始相对偏移天数
  let endDay = endDate.diff(startDateCalendar.value, 'day'); // 任务结束相对偏移天数

  if (
    (startDate.isBefore(startDateCalendar.value) && endDate.isBefore(startDateCalendar.value)) ||
    (startDate.isAfter(endDateCalendar.value) && endDate.isAfter(endDateCalendar.value))
  ) {
    itemWidth.value = 0;
    showLeftArror.value = false;
    showRightArror.value = false;
  } else if (startDate.isBefore(startDateCalendar.value) && !endDate.isAfter(endDateCalendar.value)) {
    showLeftArror.value = true;
    showRightArror.value = false;
    startDay = 0;
    itemWidth.value = (endDay - startDay + 1) * 80 - 12;
  } else if (startDate.isBefore(startDateCalendar.value) && endDate.isAfter(endDateCalendar.value)) {
    showLeftArror.value = true;
    showRightArror.value = true;
    startDay = 0;
    itemWidth.value = totalDays.value * 80 - 12;
  } else if (!startDate.isBefore(startDateCalendar.value) && endDate.isAfter(endDateCalendar.value)) {
    showLeftArror.value = false;
    showRightArror.value = true;
    itemWidth.value = (totalDays.value - startDay) * 80 - 12;
  } else {
    showLeftArror.value = false;
    showRightArror.value = false;
    itemWidth.value = (endDay - startDay + 1) * 80 - 12;
  }

  positionLeft.value = startDay * 80 + 6;
  positionTop.value = (options.value.heightLine - 1) * 72 + 11;
  barWidth.value = itemWidth.value * (options.value.percentage / 100);
};

const currentWidth = computed(() => {
  if (scrollLeft.value > positionLeft.value) {
    let width = itemWidth.value - scrollLeft.value + positionLeft.value - 1;
    return width > 0 ? width : 0;
  }
  return itemWidth.value;
});
const currentPosition = computed(() => {
  if (scrollLeft.value > positionLeft.value) {
    return scrollLeft.value;
  }
  return positionLeft.value;
});

const bgColor = computed(() => {
  let color = '';
  switch (options.value.type) {
    case 'PERSON':
      color = '#3da8f5';
      break;
    case 'GROUP':
      color = '#ff8040';
      break;
    case 'ORGANIZATION':
      color = '#4a38e6';
      break;
    case 'VERSION':
      color = '#8000ff';
      break;
    default:
      break;
  }
  return color;
});

const jumpToDetail = () => {
  getDetail(options.value);
};

// 监听heightLine变化
watch([zoomValue, dateRange, options], () => {
  if (zoomValue.value === 'day') {
    initDay();
  } else {
    initMonth();
  }
});

onMounted(() => {
  if (zoomValue.value === 'day') {
    initDay();
  } else {
    initMonth();
  }
});
</script>

<style lang="less" scoped>
.ganttitem-container {
  position: absolute;
  height: 50px;
  border-radius: 4px;
  z-index: 3;
  cursor: pointer;

  .item-wrap {
    position: relative;

    .bar {
      position: absolute;
      right: 0px;
      top: 0px;
      height: 100%;
      background-image: repeating-linear-gradient(
        135deg,
        transparent,
        transparent 10px,
        rgba(255, 255, 255, 0.55) 10px,
        rgba(255, 255, 255, 0.55) 20px
      );
    }

    .items-row-item-label {
      display: flex;
      height: 50px;
      align-items: center;

      .item-icon {
        align-items: center;
        display: flex;
        overflow: hidden;
      }

      .item-image {
        overflow: hidden;
        display: flex;
        align-items: center;
      }

      .item-text {
        margin: 4px;
        height: 100%;
        width: calc(100% - 60px);

        .item-label {
          height: 30px;
          line-height: 40px;
          color: #fff;
          font-weight: 400;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .item-description {
          height: 20px;
          font-size: 11px;
          color: #fffffff0;
          line-height: 20px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }
  }
}
</style>
