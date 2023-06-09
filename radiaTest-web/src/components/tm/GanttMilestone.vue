<template>
  <div
    class="milestone-wrap"
    :style="{
      left: calcMilestoneLeft() + 'px'
    }"
  >
    <div class="milestone-content" :style="{ top: milestoneData.height + 'px' }">
      {{ milestoneData.name }}
    </div>
  </div>
</template>

<script setup>
import dayjs from 'dayjs';

const props = defineProps(['milestoneData', 'zoomValue', 'startDateCalendar']);
const { milestoneData, zoomValue, startDateCalendar } = toRefs(props);

// 计算里程碑偏移量
const calcMilestoneLeft = () => {
  let startDay = -999;
  if (zoomValue.value === 'day' && !dayjs(milestoneData.value.startTime).isBefore(startDateCalendar.value)) {
    startDay = dayjs(milestoneData.value.startTime).diff(startDateCalendar.value, 'day');
  } else if (zoomValue.value === 'month' && !dayjs(milestoneData.value.startTime).isBefore(startDateCalendar.value)) {
    startDay = dayjs(milestoneData.value.startTime).diff(startDateCalendar.value, 'month');
  }
  return startDay * 80;
};
</script>

<style scoped lang="less">
.milestone-wrap {
  box-sizing: border-box;
  position: absolute;
  height: calc(100% + 72px);
  color: #fff;
  font-size: 10px;
  top: -72px;
  border-left: 1px solid rgb(14, 172, 81);
  z-index: 4;
  opacity: 0.2;

  &:hover {
    opacity: 1;
    z-index: 999;
  }
  .milestone-content {
    pointer-events: all;
    padding: 1px 4px;
    border-radius: 4px;
    border-bottom-left-radius: 0px;
    border-top-left-radius: 0px;
    background: rgb(14, 172, 81);
    cursor: default;
    position: absolute;
    white-space: nowrap;
    box-sizing: border-box;
    max-width: 50px;
    overflow: hidden;

    &:hover {
      max-width: max-content;
    }
  }
}
</style>
