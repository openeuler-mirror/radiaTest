<template>
  <n-grid x-gap="12" :cols="4" class="head-menu">
    <n-gi>
      <div class="menuItem">
        <div class="itemTitle">日期范围</div>
        <n-date-picker
          v-model:formattedValue="dateRange"
          type="daterange"
          @update:formatted-value="updateDateRange"
        />
      </div>
    </n-gi>
    <n-gi>
      <div class="menuItem">
        <div class="itemTitle">显示模式</div>
        <n-select v-model:value="zoomValue" :options="zoomOptions" @update:value="changeZoom" />
      </div>
    </n-gi>
    <n-gi>
      <div class="menuItem">
        <div class="itemTitle">任务类型</div>
        <n-select
          v-model:value="taskType"
          :options="taskTypeOptions"
          @update:value="changeTaskType"
        />
      </div>
    </n-gi>
    <!-- <n-gi>
      <div class="menuItem" v-show="taskType === 'group'">
        <div class="itemTitle">团队名称</div>
        <n-select v-model:value="groupValue" :options="groupOptions" @update:value="changeGroup" />
      </div>
    </n-gi> -->
  </n-grid>
  <div id="gstc" class="gstc" v-if="dataList.length">
    <div class="gstc-list">
      <div class="gstc-list-header">
        <div class="gstc-list-header-item">名称</div>
        <div class="gstc-list-header-item">类型</div>
      </div>
      <div
        class="gstc-list-rows"
        v-for="(v, i) in dataList"
        :key="i"
        :style="{
          height: getRowHeight(v.tasks) + 'px',
          lineHeight: getRowHeight(v.tasks) + 'px',
        }"
      >
        <div class="gstc-list-rows-item">
          <n-tooltip trigger="hover" placement="top-start">
            <template #trigger>
              {{ v.label }}
            </template>
            <span>{{ v.label }}</span>
          </n-tooltip>
        </div>
        <div class="gstc-list-rows-item">{{ v.type }}</div>
      </div>
    </div>
    <n-scrollbar x-scrollable trigger="none" @scroll="gstcScroll">
      <div class="gstc-chart">
        <div class="gstc-chart-calendar" v-show="zoomValue === 'day'">
          <div v-for="(v, i) in monthArray" :key="i">
            <div class="gstc-chart-calendar-level0">{{ getLevel0(v) }}</div>
            <div class="gstc-chart-calendar-level1">
              <div class="level1-item" v-for="(v1, i1) in getDays(v)" :key="i1">
                <div class="item-top">{{ v1 }}</div>
                <div class="item-bottom">{{ dayOfWeek(v, v1) }}</div>
              </div>
            </div>
          </div>
        </div>
        <div class="gstc-chart-calendar" v-show="zoomValue === 'month'">
          <div v-for="(v, i) in yearArray" :key="i">
            <div class="gstc-chart-calendar-level0">{{ v }}</div>
            <div class="gstc-chart-calendar-level1">
              <div class="level1-item" v-for="(v1, i1) in monthNameArray" :key="i1">
                <div class="item-top">{{ v1.name }}</div>
                <div class="item-bottom">{{ v1.num }}</div>
              </div>
            </div>
          </div>
        </div>
        <div class="gstc-chart-timeline">
          <GanttMilestone
            v-for="(v, i) in milestonesList"
            :key="i"
            :milestoneData="v"
            :zoomValue="zoomValue"
            :startDateCalendar="startDateCalendar"
          ></GanttMilestone>
          <div
            class="gstc-chart-timeline-row"
            v-for="(v, i) in dataList"
            :key="i"
            :style="{
              height: getRowHeight(v.tasks) + 'px',
              lineHeight: getRowHeight(v.tasks) + 'px',
            }"
          >
            <GanttItem
              v-for="(v2, i2) in v.tasks"
              :key="i2"
              :options="v2"
              :dateRange="dateRange"
              :totalDays="totalDays"
              :totalMonths="totalMonths"
              :zoomValue="zoomValue"
              :startDateCalendar="startDateCalendar"
              :endDateCalendar="endDateCalendar"
              :scrollLeft="scrollLeft"
            ></GanttItem>

            <div v-show="zoomValue === 'day'" class="cellWrap">
              <div class="gstc-chart-timeline-row-cell" v-for="(v, i) in totalDays" :key="i"></div>
            </div>
            <div v-show="zoomValue === 'month'" class="cellWrap">
              <div
                class="gstc-chart-timeline-row-cell"
                v-for="(v, i) in totalMonths"
                :key="i"
              ></div>
            </div>
          </div>
        </div>
      </div>
    </n-scrollbar>
  </div>
  <div v-else class="emptyBox">
    <n-spin :show="showSpin">
      <n-empty description="无数据"> </n-empty>
    </n-spin>
  </div>
</template>

<script setup>
import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import { getTasksGantt, getGanttMilestones, getGroup } from '@/api/get.js';
import { showModal } from '@/views/taskManage/task/modules/taskDetail.js';

dayjs.extend(customParseFormat); // 拓展支持的自定义时间格式

const dateRange = ref([
  dayjs().startOf('month').format('YYYY-MM-DD'),
  dayjs().endOf('month').format('YYYY-MM-DD'),
]); // 时间范围
const monthNum = ref(1); // 月份数量
const monthArray = ref([]); // 月份数组
const yearArray = ref([]); // 年份数组
const totalDays = ref(0); // 总天数
const totalMonths = ref(0); // 总月数
const startDateCalendar = ref(); // 日历开始日期
const endDateCalendar = ref(); // 日历结束日期
const monthNameArray = [
  { name: 'Jan', num: '01' },
  { name: 'Feb', num: '02' },
  { name: 'Mar', num: '03' },
  { name: 'Apr', num: '04' },
  { name: 'May', num: '05' },
  { name: 'Jun', num: '06' },
  { name: 'Jul', num: '07' },
  { name: 'Aug', num: '08' },
  { name: 'Sep', num: '09' },
  { name: 'Oct', num: '10' },
  { name: 'Nov', num: '11' },
  { name: 'Dec', num: '12' },
];
const zoomValue = ref('day'); // 显示模式
const zoomOptions = [
  {
    label: '按日显示',
    value: 'day',
  },
  {
    label: '按月显示',
    value: 'month',
  },
];
const scrollLeft = ref(0);

const taskType = ref('all');
const taskTypeOptions = [
  {
    label: '全部任务',
    value: 'all',
  },
  {
    label: '版本任务',
    value: 'version',
  },
  {
    label: '组织任务',
    value: 'organization',
  },
  // {
  //   label: '团队任务',
  //   value: 'group',
  // },
];
const changeTaskType = (typeValue) => {
  if (typeValue !== 'group') {
    groupValue.value = null;
  }
  getData();
};

const groupValue = ref(null);
const groupOptions = ref([]);
// const changeGroup = () => {
//   getData();
// };

// 计算月份数量、月份数组、年份数组、总天数、总月数、日历开始日期、日历结束日期
const initDate = (dateArray) => {
  showSpin.value = true;
  scrollLeft.value = 0;
  monthNum.value =
    dayjs(dateArray[1]).startOf('month').diff(dayjs(dateArray[0]).startOf('month'), 'month') + 1;
  monthArray.value = [];
  yearArray.value = [];
  totalDays.value = dayjs(dateArray[1]).diff(dateArray[0], 'day') + 1;
  totalMonths.value = 0;
  for (let i = 0; i < monthNum.value; i++) {
    let month = dayjs(dateArray[0]).month() + i;
    let year = dayjs(dateArray[0]).month(month).format('YYYY年');
    if (!yearArray.value.includes(year)) {
      yearArray.value.push(year);
    }
    monthArray.value.push(dayjs(dateArray[0]).month(month).format('YYYY-MM'));
    totalMonths.value = yearArray.value.length * 12;
  }
  if (zoomValue.value === 'day') {
    startDateCalendar.value = dateArray[0]; // 日历开始日期
    endDateCalendar.value = dateArray[1]; // 日历结束日期
  } else {
    startDateCalendar.value = dayjs(yearArray.value[0], 'YYYY年')
      .startOf('year')
      .format('YYYY-MM-DD'); // 日历开始日期
    endDateCalendar.value = dayjs(yearArray.value.at(-1), 'YYYY年')
      .endOf('year')
      .format('YYYY-MM-DD'); // 日历结束日期
  }
  getData();
};

// 月份范围变更回调
const updateDateRange = (formattedValue) => {
  dateRange.value = formattedValue;
  initDate(dateRange.value);
};

// 显示模式变更回调
const changeZoom = (value) => {
  zoomValue.value = value;
  initDate(dateRange.value);
};

// 按日显示日历一级标题
const getLevel0 = (date) => {
  return dayjs(date).format('YYYY年MM月');
};

// 按日显示日历每月天数
const getDays = (date) => {
  if (
    dayjs(date).isSame(startDateCalendar.value, 'month') &&
    dayjs(date).isSame(endDateCalendar.value, 'month')
  ) {
    let length = dayjs(endDateCalendar.value).diff(dayjs(startDateCalendar.value), 'day') + 1;
    let arr = [];
    for (let i = 0; i < length; i++) {
      arr.push(dayjs(startDateCalendar.value).date() + i);
    }
    return arr;
  } else if (dayjs(date).isSame(endDateCalendar.value, 'month')) {
    let length =
      dayjs(endDateCalendar.value).diff(dayjs(endDateCalendar.value).startOf('month'), 'day') + 1;
    return length;
  } else if (dayjs(date).isSame(startDateCalendar.value, 'month')) {
    let length =
      dayjs(startDateCalendar.value).endOf('month').diff(dayjs(startDateCalendar.value), 'day') + 1;
    let arr = [];
    for (let i = 0; i < length; i++) {
      arr.push(dayjs(startDateCalendar.value).date() + i);
    }
    return arr;
  }
  return dayjs(date).daysInMonth();
};

// 按日显示日历每天对应星期几
const dayOfWeek = (date, day) => {
  return dayjs(date).date(day).format('dddd');
};

const dataList = ref([]);

// 计算时间段是否重叠
const isOverlap = (obj1, obj2) => {
  if (
    dayjs(obj1.start_time).diff(dayjs(obj2.end_time)) <= 0 &&
    dayjs(obj1.end_time).diff(dayjs(obj2.start_time)) >= 0
  ) {
    return true;
  }
  return false;
};

// 计算heightLine
const calcHeightLine = () => {
  dataList.value.forEach((v) => {
    for (let i = 0; i < v.tasks.length; i++) {
      for (let j = 0; j < i; j++) {
        if (v.tasks[i].heightLine === v.tasks[j].heightLine) {
          let obj1 = {
            start_time: v.tasks[i].start_time,
            end_time: v.tasks[i].end_time,
          };
          let obj2 = {
            start_time: v.tasks[j].start_time,
            end_time: v.tasks[j].end_time,
          };
          if (dayjs(v.tasks[i].start_time).isBefore(dayjs(startDateCalendar.value))) {
            obj1.start_time = startDateCalendar.value;
          } else if (dayjs(v.tasks[i].end_time).isAfter(dayjs(endDateCalendar.value))) {
            obj1.end_time = endDateCalendar.value;
          }
          if (dayjs(v.tasks[j].start_time).isBefore(dayjs(startDateCalendar.value))) {
            obj2.start_time = startDateCalendar.value;
          } else if (dayjs(v.tasks[j].end_time).isAfter(dayjs(endDateCalendar.value))) {
            obj2.end_time = endDateCalendar.value;
          }
          if (isOverlap(obj1, obj2)) {
            v.tasks[i].heightLine++;
            i--;
          }
        }
      }
    }
  });
  showSpin.value = false;
};

// 根据heightLine计算行高
const getRowHeight = (tasks) => {
  let heightNum = 1;
  tasks.forEach((v) => {
    if (v.heightLine > heightNum) {
      heightNum = v.heightLine;
    }
  });
  return heightNum * 72;
};

const milestonesList = ref([]);

const getData = () => {
  dataList.value = [];
  milestonesList.value = [];
  showSpin.value = true;
  getTasksGantt({
    task_time: JSON.stringify(dateRange.value),
    type: taskType.value,
    group_id: groupValue.value,
  })
    .then((res) => {
      dataList.value = res.data;
      calcHeightLine();
    })
    .catch(() => {
      showSpin.value = false;
    });
  getGanttMilestones({ milestone_time: JSON.stringify(dateRange.value) }).then((res) => {
    let tempObj = {};
    if (zoomValue.value === 'day') {
      res.data?.forEach((item) => {
        if (!tempObj[item.start_time]) {
          tempObj[item.start_time] = [
            {
              name: item.name,
              startTime: item.start_time,
              height: 0,
            },
          ];
        } else {
          tempObj[item.start_time].push({
            name: item.name,
            startTime: item.start_time,
            height: tempObj[item.start_time].length * 20,
          });
        }
      });
    } else if (zoomValue.value === 'month') {
      res.data?.forEach((item) => {
        if (!tempObj[dayjs(item.start_time).format('YYYY-MM')]) {
          tempObj[dayjs(item.start_time).format('YYYY-MM')] = [
            {
              name: item.name,
              startTime: item.start_time,
              height: 0,
            },
          ];
        } else {
          tempObj[dayjs(item.start_time).format('YYYY-MM')].push({
            name: item.name,
            startTime: item.start_time,
            height: tempObj[dayjs(item.start_time).format('YYYY-MM')].length * 20,
          });
        }
      });
    }

    for (let i in tempObj) {
      milestonesList.value = [...tempObj[i], ...milestonesList.value];
    }
  });
};

const getGroupOptions = () => {
  groupOptions.value = [];
  getGroup({
    page_num: 1,
    page_size: 999999,
  }).then((res) => {
    res.data?.items?.forEach((item) => {
      groupOptions.value.push({
        label: item.name,
        value: item.id,
      });
    });
  });
};

const gstcScroll = (e) => {
  scrollLeft.value = e.target.scrollLeft;
};

const showSpin = ref(false);

// 任务详情页关闭回调
watch(showModal, () => {
  if (!showModal.value) {
    initDate(dateRange.value);
  }
});

onMounted(() => {
  initDate(dateRange.value);
  getGroupOptions();
});
</script>

<style lang="less" scoped>
* {
  box-sizing: border-box;
}

:deep(.n-scrollbar-rail--horizontal) {
  z-index: 10;
}

.menuItem {
  display: flex;
  align-items: center;

  .itemTitle {
    white-space: nowrap;
    margin-right: 5px;
  }
}
.gstc {
  display: flex;
  padding: 30px 50px;
  --height: 72px;
  --width: 80px;

  .gstc-list {
    .gstc-list-header {
      display: flex;

      .gstc-list-header-item {
        background: #f9fafb;
        color: #707070;
        text-align: center;
        font-weight: 500;
        line-height: var(--height);
        height: var(--height);
        width: var(--width);
        border-top: 1px solid #a9aeafbf;
        border-right: 1px solid #a9aeafbf;
        border-bottom: 1px solid #a9aeafbf;

        &:first-child {
          border-left: 1px solid #a9aeafbf;
        }
      }
    }

    .gstc-list-rows {
      display: flex;

      .gstc-list-rows-item {
        background: #fdfdfd;
        width: var(--width);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        text-align: center;
        border-right: 1px solid #a9aeafbf;
        border-bottom: 1px solid #a9aeafbf;
        &:first-child {
          border-left: 1px solid #a9aeafbf;
        }
      }
    }
  }

  .gstc-chart {
    overflow: hidden;
    .gstc-chart-calendar {
      background: #f9fafb;
      color: #747a81;
      user-select: none;
      display: flex;
      min-width: max-content;

      .gstc-chart-calendar-level0 {
        font-size: 14px;
        height: 21px;
        white-space: nowrap;
        border-top: 1px solid #a9aeafbf;
        border-right: 1px solid #a9aeafbf;
      }
      .gstc-chart-calendar-level1 {
        height: 51px;
        display: flex;

        .level1-item {
          width: 80px;
          text-align: center;
          font-size: 18px;
          line-height: 1.6em;
          white-space: nowrap;
          border-right: 1px solid #a9aeafbf;
          border-bottom: 1px solid #a9aeafbf;

          .item-bottom {
            font-size: 13px;
            font-weight: 300;
            line-height: 1em;
          }
        }
      }
    }

    .gstc-chart-timeline {
      position: relative;

      .gstc-chart-timeline-row {
        height: var(--height);
        line-height: var(--height);
        position: relative;

        .cellWrap {
          display: flex;
          height: 100%;

          .gstc-chart-timeline-row-cell {
            flex-shrink: 0;
            width: var(--width);
            height: 100%;
            overflow: hidden;
            border-right: 1px solid #a9aeafbf;
            border-bottom: 1px solid #a9aeafbf;
          }
        }
      }
    }
  }
}

.emptyBox {
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.head-menu {
  padding: 0px 50px;
}
</style>
