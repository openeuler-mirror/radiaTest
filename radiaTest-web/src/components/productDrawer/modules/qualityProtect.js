import { ref } from 'vue';
import { getQualityDefend } from '@/api/get';

const showCard = ref('daily-build');

const atProgress = ref(0);
const atPassed = ref(null);
const dailyBuildCompletion = ref(0);
const dailyBuildPassed = ref(null);
const weeklybuildHealth = ref(0);
const weeklybuildPassed = ref(null);
const rpmCheckProgress = ref(0);

const handleMouseEnter = (id) => {
  document.getElementById(id).style.boxShadow = '0px 0px 20px #f3f3f3';
};

const handleMouseLeave = (id) => {
  document.getElementById(id).style.boxShadow = 'none';
};

const handleClick = (id) => {
  document.getElementsByClassName('item').forEach((el) => {
    el.style.borderBottom = 'none';
  });
  showCard.value = id;
  document.getElementById(id).style.borderBottom = '3px solid #e2e2e2';
};

function getStatistic(id) {
  getQualityDefend(id).then((res) => {
    const atStatistic = res.data.at_statistic;
    if (atStatistic) {
      atProgress.value = Math.round((atStatistic.success / atStatistic.total) * 100);
      atPassed.value = atStatistic.passed;
    }
    dailyBuildCompletion.value = res.data.dailybuild_statistic?.completion;
    dailyBuildPassed.value = res.data.dailybuild_statistic?.passed;
    weeklybuildHealth.value = res.data.weeklybuild_statistic?.health_rate;
    weeklybuildPassed.value = res.data.weeklybuild_statistic?.health_passed;
    rpmCheckProgress.value = res.data.rpmcheck_statistic?.succeeded_rate?.replace('%', '');
  });
}

function renderColor(isPassed) {
  if (isPassed === true) {
    return '#18A058';
  } else if (isPassed === false) {
    return '#C20000';
  }
  return undefined;
}

function cleanQualityProtectData() {
  atProgress.value = 0;
  dailyBuildCompletion.value = 0;
  weeklybuildHealth.value = 0;
  weeklybuildHealth.value = 0;
}

export {
  renderColor,
  getStatistic,
  atProgress,
  atPassed,
  handleMouseEnter,
  handleMouseLeave,
  handleClick,
  showCard,
  dailyBuildCompletion,
  dailyBuildPassed,
  weeklybuildHealth,
  weeklybuildPassed,
  rpmCheckProgress,
  cleanQualityProtectData
};
