import { ref } from 'vue';
import { getQualityDefend } from '@/api/get';

const showCard = ref('daily-build');

const atProgress = ref(0);
const dailyBuildCompletion = ref(0);
const weeklybuildHealth = ref(0);
const weeklybuildHealthBaseline = ref(0);

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

function getStatistic (id) {
  getQualityDefend(id)
    .then(res => {
      const atStatistic = res.data.at_statistic;
      atProgress.value = Math.round(atStatistic.success / atStatistic.total * 100);
      dailyBuildCompletion.value = res.data.dailybuild_statistic?.completion;
      weeklybuildHealth.value = res.data.weeklybuild_statistic?.health_rate;
      weeklybuildHealthBaseline.value = res.data.weeklybuild_statistic?.health_baseline;
    });
}

function weeklybuildHealthColor() {
  if (weeklybuildHealth.value >= weeklybuildHealthBaseline.value) {
    return '#18A058';
  }
  return '#C20000';
}

export {
  weeklybuildHealthColor,
  getStatistic,
  atProgress,
  handleMouseEnter,
  handleMouseLeave,
  handleClick,
  showCard,
  dailyBuildCompletion,
  weeklybuildHealth,
};
