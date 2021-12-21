<template>
  <div :id="'echart' + chartId" style="height:100%">
    <div v-if="option.series[0].data.length === 0" style="height:100%">
      <p class="chartTitle">{{ option.title.text }}</p>
      <div class="centerBox">
        <n-empty description="暂无数据"> </n-empty>
      </div>
    </div>
  </div>
</template>
<script>
import { init } from 'echarts';
import { onMounted, watch, nextTick } from 'vue';

export default {
  props: {
    option: {
      type: Object,
      required: true,
    },
    chartId: {
      type: String,
      default: 'chart',
    },
  },
  setup(props) {
    let chart;
    function createDom(id) {
      const div = document.createElement('div');
      div.id = id;
      div.style = 'height:100%;';
      document.querySelector(`#echart${props.chartId}`).appendChild(div);
    }
    onMounted(() => {
      if (props.option.series[0].data.length) {
        if (!document.querySelector(`#${props.chartId}`)) {
          createDom(props.chartId);
        }
        chart?.clear();
        chart = init(document.querySelector(`#${props.chartId}`));
        chart.setOption(props.option);
      }
    });
    watch(
      props.option,
      (newVal) => {
        if (props.option.series[0].data.length) {
          if (!document.querySelector(`#${props.chartId}`)) {
            createDom(props.chartId);
          }
          if(!chart){
            chart = init(document.querySelector(`#${props.chartId}`));
          }
          chart?.clear();
          nextTick(() => {
            chart?.setOption(newVal);
          });
        } else {
          chart?.dispose();
        }
      },
      {
        deep: true,
      }
    );
  },
};
</script>
<style scoped>
.chartTitle {
  font-size: 18px;
  font-weight: bolder;
}
.centerBox {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}
</style>
