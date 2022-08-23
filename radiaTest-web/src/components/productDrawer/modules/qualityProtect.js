import { ref } from 'vue';
import { getQualityDefend } from '@/api/get';

const showCard = ref('daily-build');

const atProgress = ref(0);
const dailyBuildCompletion = ref(0);

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
    });
}

export {
  getStatistic,
  atProgress,
  handleMouseEnter,
  handleMouseLeave,
  handleClick,
  showCard,
  dailyBuildCompletion
};
