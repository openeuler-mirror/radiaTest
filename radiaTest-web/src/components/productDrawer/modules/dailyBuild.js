import { NProgress } from 'naive-ui';
import { h, ref } from 'vue';
import { getDailyBuildSingle, getDailyBuildBatch } from '@/api/get';

const dailyBuildList = ref([]);
const listLoading = ref(false);
const totalNum = ref(0);

const getDailyBuildList = (qualityBoardId, params) => {
  listLoading.value = true;
  getDailyBuildBatch(qualityBoardId, params)
    .then((res) => {
      dailyBuildList.value = res.data.items;
      totalNum.value = res.data.total;
    })
    .finally(() => {
      listLoading.value = false;
    });
};

const dailyBuildColumns = ref([
  {
    title: '构建记录',
    key: 'name',
  },
  {
    title: '构建完成度',
    key: 'completion',
    className: 'completion',
    render: (row) => {
      return h(
        NProgress,
        {
          type: 'line',
          percentage: row.completion,
          indicatorPlacement: 'inside',
          status: row.completion === 100 ? 'success' : 'error'
        }
      );
    }
  }
]);

const treeShow = ref(false);
const currentBuild = ref();
const buildTreeOption = ref({
  tooltip: {
    trigger: 'item',
    triggerOn: 'mousemove'
  },
  series: [
    {
      type: 'tree',
      id: 0,
      name: 'buildTree',
      top: '0%',
      left: '10%',
      bottom: '0%',
      right: '10%',
      symbol: 'emptyCircle',
      symbolSize: 7,
      edgeShape: 'polyline',
      edgeForkPosition: '50%',
      roam: true,
      initialTreeDepth: 10,
      lineStyle: {
        width: 2
      },
      label: {
        backgroundColor: '#fff',
        position: 'left',
        verticalAlign: 'middle',
        align: 'right'
      },
      leaves: {
        label: {
          position: 'right',
          verticalAlign: 'middle',
          align: 'left'
        }
      },
      emphasis: {
        focus: 'descendant'
      },
      expandAndCollapse: true,
      animationDuration: 550,
      animationDurationUpdate: 750
    }
  ]
});

const getDailyBuildData = (dailyBuildId) => {
  getDailyBuildSingle(dailyBuildId)
    .then((res) => {
      buildTreeOption.value.series[0].data = [JSON.parse(res.data.detail)];
      currentBuild.value = res.data.name;
      treeShow.value = true;
    });
};

function handleDailyBuildClick(row) {
  currentBuild.value = row.name;
  getDailyBuildData(row.id);
}

function handleTreeClose() {
  treeShow.value = false;
  currentBuild.value = undefined;
}

function cleanList() {
  dailyBuildList.value = [];
  totalNum.value = 0;
}

export {
  dailyBuildColumns,
  dailyBuildList,
  listLoading,
  treeShow,
  totalNum,
  getDailyBuildList,
  getDailyBuildData,
  currentBuild,
  buildTreeOption,
  handleDailyBuildClick,
  handleTreeClose,
  cleanList,
};
