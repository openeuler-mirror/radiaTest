import { h,ref,watch,nextTick } from 'vue';
import { 
  getFeatureCompletionRates, 
  getFeatureList as getFeatureData, 
  getPackageListComparationSummary as getPackageData,
  getPackageListComparationDetail as getPackageChangeSummary,
} from '@/api/get';
import { NButton, NTag, NSpace } from 'naive-ui';
import { list, currentId, preId } from './productTable';

const detail = ref({});
const drawerShow = ref(false);
const active = ref(false);
const requestCard = ref(null);
const cardDescription = ref({
  title: null,
  progress: null,
});
function cardClick () {
  active.value = true;
}
const activeTab = ref('testProgress');
const testProgressList = ref([]);

const boxWidth = ref(0);

const oldPackage = ref({
  size: 0,
  name: null
});
const newPackage = ref({
  size: 0,
  name: null
});
const packageChangeSummary = ref({
  addPackagesNum: 0,
  delPackagesNum: 0
});

function getPackageListComparationSummary(qualityboardId, _refresh = false) {
  const idList = list.value.map(item => item.key);
  const currentIndex = idList.indexOf(currentId.value);
  if ( currentIndex === 0) {
    // 暂时设为round1，未来设置为前正式发布版本的release里程碑
    preId.value = currentId.value;
    getPackageData(qualityboardId, currentId.value, { summary: true, refresh: _refresh })
      .then((res) => {
        if (!_refresh) {
          newPackage.value.size = res.data.size;
          newPackage.value.name = res.data.name;
          oldPackage.value.size = res.data.size;
          oldPackage.value.name = res.data.name;
          packageChangeSummary.value.addPackagesNum = 0;
          packageChangeSummary.value.delPackagesNum = 0;
        } else {
          window.$message?.info(res.error_msg, { duration: 8e3 });
        }
      });
  } else {
    preId.value = idList[currentIndex - 1];
    getPackageData(qualityboardId, preId.value, { summary: true, refresh: _refresh })
      .then((res) => {
        if (!_refresh) {
          oldPackage.value.size = res.data.size;
          oldPackage.value.name = res.data.name;
        } else {
          window.$message?.info(res.error_msg, { duration: 8e3 });
        }
      });
    getPackageData(qualityboardId, currentId.value, { summary: true, refresh: _refresh })
      .then((res) => {
        if (!_refresh) {
          newPackage.value.size = res.data.size;
          newPackage.value.name = res.data.name;
        } else {
          window.$message?.info(res.error_msg, { duration: 8e3 });
        }
      });
    getPackageChangeSummary(qualityboardId, preId.value, currentId.value, { summary: true })
      .then((res) => {
        packageChangeSummary.value.addPackagesNum = res.data.add_pkgs_num;
        packageChangeSummary.value.delPackagesNum = res.data.del_pkgs_num;
      })
      .catch(() => {
        packageChangeSummary.value.addPackagesNum = '?';
        packageChangeSummary.value.delPackagesNum = '?';
      });
  }
}

const showPackage = ref(false);
const packageBox = ref(null);
const packageWidth = ref(0);
watch(showPackage, () => {
  nextTick(() => {
    packageWidth.value = requestCard.value.$el.clientWidth;
  });
});

const featureListColumns = [
  {
    key: 'no',
    title: '编号',
    className: 'feature-no',
    render: (row) => {
      return h(
        NButton,
        {
          type: 'info',
          text: true,
          onClick: () => {
            window.open(row.url);
          }
        },
        row.no
      );
    }
  },
  {
    key: 'feature',
    title: '特性',
    className: 'feature-name',
  },
  {
    key: 'sig',
    title: '归属SIG',
    className: 'feature-sig',
    render: (row) => {
      return row.sig?.map((item) => h(
        NButton, 
        {
          type: 'info',
          text: true,
          style: {
            padding: '5px',
            display: 'block',
          },
          onClick: () => {}
        }, 
        item
      ));
    }
  },
  {
    key: 'owner',
    title: '责任人',
    className: 'feature-owner',
    render: (row) => {
      return row.owner?.map((item) => h(
        NButton, 
        {
          type: 'info',
          text: true,
          style: {
            padding: '5px',
            display: 'block',
          },
          onClick: () => {}
        }, 
        item
      ));
    }
  },
  {
    key: 'release-to',
    title: '发布方式',
    className: 'feature-release-to',
  },
  {
    key: 'pkgs',
    title: '影响软件包范围',
    className: 'feature-pkgs',
    render: (row) => {
      return h(
        NSpace,
        {},
        row.pkgs?.map((item) => h(NTag, {}, item))
      );
    }
  },
  {
    key: 'task_status',
    title: '测试任务状态',
    className: 'feature-task-status',
  }
];

const additionFeatureCount = ref(0);
const inheritFeatureCount = ref(0);
const additionFeatureRate = ref(0);
const inheritFeatureRate = ref(0);

const featureLoading = ref(false);
const featureListData = ref([]);
const showList = ref(false);

function handleListClick() {
  showList.value = true;
}

function getFeatureList(qualityboardId, _type) {
  featureLoading.value = true;
  getFeatureData(qualityboardId, { new: _type === 'addition' })
    .then((res) => {
      featureListData.value = res.data;
    })
    .finally(() => { featureLoading.value = false; });
} 

function getFeatureSummary(qualityboardId) {
  getFeatureCompletionRates(qualityboardId)
    .then((res) => {
      additionFeatureRate.value = res.data.addition_feature_rate;
      additionFeatureCount.value = res.data.addition_feature_count;
      inheritFeatureRate.value = res.data.inherit_feature_rate;
      inheritFeatureCount.value = res.data.inherit_feature_count;
    });
}

function cleanData() {
  featureLoading.value = false;
  featureListData.value = [];
}

watch(showList, () => {
  nextTick(() => {
    boxWidth.value = requestCard.value.$el.clientWidth;
  });
});

export {
  packageBox,
  showPackage,
  requestCard,
  newPackage,
  showList,
  oldPackage,
  packageWidth,
  boxWidth,
  additionFeatureRate,
  inheritFeatureRate,
  additionFeatureCount,
  inheritFeatureCount,
  activeTab,
  active,
  detail,
  testProgressList,
  drawerShow,
  cardDescription,
  cardClick,
  handleListClick,
  getFeatureSummary,
  cleanData,
  getFeatureList,
  featureListColumns,
  featureListData,
  featureLoading,
  getPackageListComparationSummary,
  packageChangeSummary,
};
