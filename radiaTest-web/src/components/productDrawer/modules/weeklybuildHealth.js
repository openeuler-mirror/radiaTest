import { h, ref } from 'vue';
import { NTag, NIcon } from 'naive-ui';
import { CancelRound, CheckCircleFilled } from '@vicons/material';
import { QuestionCircle16Filled } from '@vicons/fluent';
import { getWeeklybuildData, getWeeklybuildDetail } from '@/api/get';

const weeklybuildColumns = ref([
  {
    key: 'start_time',
    title: '开始时间',
  },
  {
    key: 'end_time',
    title: '结束时间',
  },
  {
    key: 'build_passed_rate',
    title: '构建通过率',
    render: (row) => h('span', null, `${row.build_passed_rate}%`)
  },
  {
    key: 'at_passed_rate',
    title: 'AT通过率',
    render: (row) => h('span', null, `${row.at_passed_rate}%`)
  },
  {
    key: 'health_rate',
    title: '健康度',
    render (row) {
      if (row.health_baseline !== null
        && row.health_rate !== null
        && row.health_rate >= row.health_baseline) {
        return h(
          NTag,
          {
            type: 'success',
            round: true,
            bordered: false,
          },
          {
            default: `${row.health_rate}%`,
            icon: () => h(NIcon, {
              component: CheckCircleFilled 
            })
          }
        );
      } else if (row.health_rate === null || !row.health_baseline === null) {
        return h(
          NTag,
          {
            type: 'default',
            round: true,
            bordered: false,
          },
          {
            default: 'unknown',
            icon: () => h(NIcon, {
              component: QuestionCircle16Filled 
            })
          }
        );
      }
      return h(
        NTag,
        {
          type: 'error',
          round: true,
          bordered: false,
        },
        {
          default: `${row.health_rate}%`,
          icon: () => h(NIcon, {
            component: CancelRound 
          })
        }
      );
    }
  }
]);

const loading = ref(false);
const totalNum = ref(0);
const weeklybuildData = ref([]);

function getData(qualityBoardId, params) {
  loading.value = true;
  getWeeklybuildData(qualityBoardId, params)
    .then((res) => {
      weeklybuildData.value = res.data.items;
      totalNum.value = res.data.total;
    })
    .finally(() => {
      loading.value = false;
    });
}

const detailColumns = ref([
  {
    key: 'name',
    title: '构建名',
  },
  {
    key: 'build_passed',
    title: '构建成功',
    render: (row) => {
      if (row.build_passed) {
        return h(NIcon, {
          color: '#18A058',
          size: 24,
          component: CheckCircleFilled 
        });
      }
      return h(NIcon, {
        color: '#C20000',
        size: 24,
        component: CancelRound 
      });
    }
  },
  {
    key: 'at_passed',
    title: 'AT达标',
    render: (row) => {
      if (row.at_passed) {
        return h(NIcon, {
          color: '#18A058',
          size: 24,
          component: CheckCircleFilled 
        });
      }
      return h(NIcon, {
        color: '#C20000',
        size: 24,
        component: CancelRound 
      });
    }
  },
]);

const weekShow = ref(false);
const weekStartDate = ref();
const weekEndDate = ref();
const detailLoading = ref(false);
const detailData = ref([]);

function handleWeekClick(row) {
  weekShow.value = true;
  weekStartDate.value = row.start_time,
  weekEndDate.value = row.end_time,
  detailLoading.value = true;
  getWeeklybuildDetail(row.id)
    .then((res) => {
      detailData.value = res.data;
    })
    .finally(() => {
      detailLoading.value = false;
    });
}

const cleanData = () => {
  weeklybuildData.value = [];
  totalNum.value = 0;
  detailData.value = [];
  weekStartDate.value = null;
  weekEndDate.value = null;
  weekShow.value = false;
};

export {
  weeklybuildColumns,
  getData,
  weeklybuildData,
  totalNum,
  loading,
  cleanData,
  handleWeekClick,
  weekStartDate,
  weekEndDate,
  detailColumns,
  detailData,
  detailLoading,
  weekShow
};
