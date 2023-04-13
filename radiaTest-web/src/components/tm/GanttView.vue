<template>
  <n-grid x-gap="12" :cols="4">
    <n-gi>
      <div class="menuItem">
        <div class="itemTitle">月份范围</div>
        <n-date-picker
          v-model:formattedValue="monthRangeValue"
          type="monthrange"
          @update:formatted-value="updateMonthRange"
        />
      </div>
    </n-gi>
    <n-gi>
      <div class="menuItem">
        <div class="itemTitle">显示模式</div>
        <n-select v-model:value="zoomValue" :options="zoomOptions" @update:value="changeZoom" />
      </div>
    </n-gi>
  </n-grid>
  <div id="gstc" class="gstc" v-if="dataList.length">
    <div class="gstc-list">
      <div class="gstc-list-header">
        <div class="gstc-list-header-item">ID</div>
        <div class="gstc-list-header-item">Label</div>
        <div class="gstc-list-header-item">Progress</div>
      </div>
      <div
        class="gstc-list-rows"
        v-for="(v, i) in dataList"
        :key="i"
        :style="{
          height: getRowHeight(v.tasks) + 'px',
          lineHeight: getRowHeight(v.tasks) + 'px'
        }"
      >
        <div class="gstc-list-rows-item">{{ v.id }}</div>
        <div class="gstc-list-rows-item">{{ v.label }}</div>
        <div class="gstc-list-rows-item">{{ v.progress }}</div>
      </div>
    </div>
    <n-scrollbar x-scrollable trigger="none">
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
          <div
            class="gstc-chart-timeline-row"
            v-for="(v, i) in dataList"
            :key="i"
            :style="{
              height: getRowHeight(v.tasks) + 'px',
              lineHeight: getRowHeight(v.tasks) + 'px'
            }"
          >
            <GanttItem
              v-for="(v2, i2) in v.tasks"
              :key="i2"
              :options="v2"
              :monthRangeValue="monthRangeValue"
              :totalDays="totalDays"
              :totalMonths="totalMonths"
              :zoomValue="zoomValue"
              :startDateCalendar="startDateCalendar"
              :endDateCalendar="endDateCalendar"
            ></GanttItem>
            <div v-show="zoomValue === 'day'" class="cellWrap">
              <div class="gstc-chart-timeline-row-cell" v-for="(v, i) in totalDays" :key="i"></div>
            </div>
            <div v-show="zoomValue === 'month'" class="cellWrap">
              <div class="gstc-chart-timeline-row-cell" v-for="(v, i) in totalMonths" :key="i"></div>
            </div>
          </div>
        </div>
      </div>
    </n-scrollbar>
  </div>
  <div v-else class="emptyBox">
    <n-empty description="无数据"> </n-empty>
  </div>
</template>

<script setup>
import dayjs from 'dayjs';
import customParseFormat from 'dayjs/plugin/customParseFormat';
import _ from 'lodash';

dayjs.extend(customParseFormat);
const monthRangeValue = ref(['2023-01', '2023-01']); // 时间范围
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
  { name: 'Dec', num: '12' }
];
const zoomValue = ref('day'); // 显示模式
const zoomOptions = [
  {
    label: '按日显示',
    value: 'day'
  },
  {
    label: '按月显示',
    value: 'month'
  }
];

const initDate = (dateArray) => {
  monthNum.value = dayjs(dateArray[1]).diff(dateArray[0], 'month') + 1;
  monthArray.value = [];
  yearArray.value = [];
  totalDays.value = 0;
  totalMonths.value = 0;
  for (let i = 0; i < monthNum.value; i++) {
    let month = dayjs(dateArray[0]).month() + i;
    let year = dayjs(dateArray[0]).month(month).format('YYYY年');
    if (!yearArray.value.includes(year)) {
      yearArray.value.push(year);
    }
    monthArray.value.push(dayjs(dateArray[0]).month(month).format('YYYY-MM'));
    totalDays.value = totalDays.value + dayjs(dateArray[0]).month(month).daysInMonth();
    totalMonths.value = yearArray.value.length * 12;
  }
  if (zoomValue.value === 'day') {
    startDateCalendar.value = dayjs(monthArray.value[0]).format('YYYY-MM-DD'); // 日历开始日期
    endDateCalendar.value = dayjs(monthArray.value.at(-1)).endOf('month').format('YYYY-MM-DD'); // 日历结束日期
  } else {
    startDateCalendar.value = dayjs(yearArray.value[0], 'YYYY年').startOf('year').format('YYYY-MM-DD'); // 日历开始日期
    endDateCalendar.value = dayjs(yearArray.value.at(-1), 'YYYY年').endOf('year').format('YYYY-MM-DD'); // 日历结束日期
  }
  calcHeightLine();
};

// 月份范围变更回调
const updateMonthRange = (formattedValue) => {
  // TODO
  dataList.value = _.cloneDeep(dataListTemp.value);

  monthRangeValue.value = formattedValue;
  initDate(monthRangeValue.value);
};

// 显示模式变更回调
const changeZoom = (value) => {
  zoomValue.value = value;
  initDate(monthRangeValue.value);
};

const getLevel0 = (date) => {
  return dayjs(date).format('YYYY年MM月');
};

const getDays = (date) => {
  return dayjs(date).daysInMonth();
};

const dayOfWeek = (date, day) => {
  return dayjs(date).date(day).format('dddd');
};

const dataList = ref([]);

// 按月显示测试数据
// const dataList = ref([
//   {
//     id: 0,
//     label: 'Jhon Doe 0',
//     progress: 48,
//     tasks: [
//       {
//         id: 0,
//         heightLine: 1,
//         start_time: '2022-11-5',
//         end_time: '2022-12-25',
//         url: 'www.baidu.com',
//         name: 'Task Name1',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 0,
//         heightLine: 1,
//         start_time: '2024-1-5',
//         end_time: '2024-2-25',
//         url: 'www.baidu.com',
//         name: 'Task Name2',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 0,
//         heightLine: 1,
//         start_time: '2022-10-5',
//         end_time: '2023-3-5',
//         url: 'www.baidu.com',
//         name: 'Task Name3',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 0,
//         heightLine: 1,
//         start_time: '2022-5-5',
//         end_time: '2024-7-25',
//         url: 'www.baidu.com',
//         name: 'Task Name4',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 0,
//         heightLine: 1,
//         start_time: '2023-10-5',
//         end_time: '2024-3-5',
//         url: 'www.baidu.com',
//         name: 'Task Name5',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 0,
//         heightLine: 1,
//         start_time: '2023-5-5',
//         end_time: '2023-7-25',
//         url: 'www.baidu.com',
//         name: 'Task Name6',
//         description: 'this is a description',
//         percentage: 0.5
//       }
//     ]
//   },
//   {
//     id: 1,
//     label: 'Jhon Doe 1',
//     progress: 48,
//     tasks: []
//   },
//   { id: 2, label: 'Jhon Doe 2', progress: 48, tasks: [] },
//   { id: 3, label: 'Jhon Doe 3', progress: 48, tasks: [] },
//   { id: 4, label: 'Jhon Doe 4', progress: 48, tasks: [] },
//   { id: 5, label: 'Jhon Doe 5', progress: 48, tasks: [] }
// ]);

// 按日显示测试数据
// const dataList = ref([
//   {
//     id: 0,
//     label: 'Jhon Doe 0',
//     progress: 48,
//     tasks: [
//       {
//         id: 0,
//         heightLine: 1,
//         start_time: '2022-12-15',
//         end_time: '2022-12-31',
//         url: 'www.baidu.com',
//         name: 'Task Name1',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 0,
//         heightLine: 1,
//         start_time: '2022-12-31',
//         end_time: '2023-1-1',
//         url: 'www.baidu.com',
//         name: 'Task Name2',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 0,
//         heightLine: 1,
//         start_time: '2022-12-6',
//         end_time: '2023-2-10',
//         url: 'www.baidu.com',
//         name: 'Task Name3',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 0,
//         heightLine: 1,
//         start_time: '2023-1-5',
//         end_time: '2023-1-10',
//         url: 'www.baidu.com',
//         name: 'Task Name4',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 0,
//         heightLine: 1,
//         start_time: '2023-1-12',
//         end_time: '2023-2-5',
//         url: 'www.baidu.com',
//         name: 'Task Name5',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 0,
//         heightLine: 1,
//         start_time: '2023-2-1',
//         end_time: '2023-2-2',
//         url: 'www.baidu.com',
//         name: 'Task Name6',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 0,
//         heightLine: 1,
//         start_time: '2022-11-1',
//         end_time: '2022-12-1',
//         url: 'www.baidu.com',
//         name: 'Task Name7',
//         description: 'this is a description',
//         percentage: 0.5
//       }
//     ]
//   },
//   {
//     id: 1,
//     label: 'Jhon Doe 1',
//     progress: 48,
//     tasks: [
//       {
//         id: 1,
//         heightLine: 1,
//         start_time: '2022-12-31',
//         end_time: '2022-12-31',
//         url: 'www.baidu.com',
//         name: 'Task Name1',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 1,
//         heightLine: 1,
//         start_time: '2022-12-31',
//         end_time: '2023-1-1',
//         url: 'www.baidu.com',
//         name: 'Task Name2',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 1,
//         heightLine: 1,
//         start_time: '2022-12-31',
//         end_time: '2023-1-31',
//         url: 'www.baidu.com',
//         name: 'Task Name3',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 1,
//         heightLine: 1,
//         start_time: '2022-12-31',
//         end_time: '2023-2-1',
//         url: 'www.baidu.com',
//         name: 'Task Name4',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 1,
//         heightLine: 1,
//         start_time: '2023-1-1',
//         end_time: '2023-1-1',
//         url: 'www.baidu.com',
//         name: 'Task Name5',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 1,
//         heightLine: 1,
//         start_time: '2023-1-1',
//         end_time: '2023-1-31',
//         url: 'www.baidu.com',
//         name: 'Task Name6',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 1,
//         heightLine: 1,
//         start_time: '2023-1-1',
//         end_time: '2023-2-1',
//         url: 'www.baidu.com',
//         name: 'Task Name7',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 1,
//         heightLine: 1,
//         start_time: '2023-1-31',
//         end_time: '2023-1-31',
//         url: 'www.baidu.com',
//         name: 'Task Name8',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 1,
//         heightLine: 1,
//         start_time: '2023-1-31',
//         end_time: '2023-2-1',
//         url: 'www.baidu.com',
//         name: 'Task Name9',
//         description: 'this is a description',
//         percentage: 0.5
//       },
//       {
//         id: 1,
//         heightLine: 1,
//         start_time: '2023-2-1',
//         end_time: '2023-2-1',
//         url: 'www.baidu.com',
//         name: 'Task Name10',
//         description: 'this is a description',
//         percentage: 0.5
//       }
//     ]
//   },
//   { id: 2, label: 'Jhon Doe 2', progress: 48, tasks: [] },
//   { id: 3, label: 'Jhon Doe 3', progress: 48, tasks: [] },
//   { id: 4, label: 'Jhon Doe 4', progress: 48, tasks: [] },
//   { id: 5, label: 'Jhon Doe 5', progress: 48, tasks: [] }
// ]);

// TODO
const dataListTemp = ref(_.cloneDeep(dataList.value));

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
            end_time: v.tasks[i].end_time
          };
          let obj2 = {
            start_time: v.tasks[j].start_time,
            end_time: v.tasks[j].end_time
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
            return calcHeightLine();
          }
        }
      }
    }
    return true;
  });
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

onMounted(() => {
  initDate(monthRangeValue.value);
});
</script>

<style lang="less" scoped>
* {
  box-sizing: border-box;
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
  padding: 50px;
  // overflow: scroll;
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
</style>
