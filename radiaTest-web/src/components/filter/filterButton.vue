<template>
  <div>
    <n-popover trigger="manual" :show="showPopover" placement="bottom-end" :show-arrow="false" @clickoutside="clickOutside">
      <template #trigger>
        <a class="filterWrap" @click="clickFilter">
          <n-icon size="16"><Filter /></n-icon>筛选
        </a>
      </template>
      <n-card
        title="筛选条件"
        closable
        content-style="width:800px"
        :bordered="false"
        :segmented="{
          content: true,
          footer: true
        }"
        @close="handleClose"
      >
        <div class="selectLine" v-for="(item, index) in filterArray" :key="index">
          <div class="circleNumber item">{{ index + 1 }}</div>
          <div class="item">{{ index === 0 ? '当' : '且' }}</div>
          <div class="item filterName">
            <n-select v-model:value="item.name" :options="filterOption" @update:value="selectFilterName(index, $event)" />
          </div>
          <div class="item filterCondition">
            <n-select disabled v-if="!item.name" />
            <n-select disabled v-else v-model:value="item.condition" />
          </div>
          <div class="item filterValue">
            <n-input type="text" v-if="!item.name" disabled />
            <n-input type="text" v-else-if="item.type === 'input'" @input="item.cb(item)" v-model:value="item.value" />
            <n-select v-else-if="item.type === 'select'" v-model:value="item.value" :options="item.options" filterable />
            <n-select v-else-if="item.type === 'multipleselect'" multiple v-model:value="item.value" :options="item.options" filterable />
            <n-date-picker type="date" v-else-if="(item.type === 'startdate') | (item.type === 'enddate')" v-model:value="item.value" />
          </div>
          <div class="item filterDelete" @click="clickDelete(index)">
            <n-icon size="16"><Delete24Regular /></n-icon>
          </div>
        </div>
        <div :class="['addBtn', addFlag ? '' : 'notAllowed']" @click="clickAdd">
          <n-icon size="16"><Add /></n-icon>&nbsp;添加
        </div>
        <template #footer>
          <div class="btnWrap">
            <div class="resetBtnWrap">
              <n-button class="btn" @click="clickReset">重置</n-button>
            </div>
            <div class="cancelConfirmBtnWrap">
              <n-button class="btn" @click="handleClose">取消</n-button>
              <n-button class="btn" type="info" @click="confirmFilter">
                筛选
              </n-button>
            </div>
          </div>
        </template>
      </n-card>
    </n-popover>
  </div>
</template>

<script>
import { Filter } from '@vicons/tabler';
import { Add } from '@vicons/ionicons5';
import { Delete24Regular } from '@vicons/fluent';
import { ref, computed } from 'vue';

export default {
  components: {
    Filter,
    Add,
    Delete24Regular
  },
  props: ['filterRule'],
  emits: ['filterchange'],
  // eslint-disable-next-line max-lines-per-function
  setup(props, context) {
    const showPopover = ref(false); // 显示筛选框
    const filterArray = ref([]); // 已选择的筛选条件

    const clickFilter = () => {
      showPopover.value = true;
    };

    const handleClose = () => {
      showPopover.value = false;
    };

    const clickOutside = () => {
      showPopover.value = false;
    };

    // 删除筛选条件
    const clickDelete = (index) => {
      filterArray.value.splice(index, 1);
    };

    // 重置
    const clickReset = () => {
      filterArray.value = [];
      let tempArr = [];
      props.filterRule.forEach((v) => {
        tempArr.push({
          path: v.path,
          value: null
        });
      });
      context.emit('filterchange', tempArr);
      showPopover.value = false;
    };

    const filterCondition = (type) => {
      let condition = '';
      switch (type) {
        case 'input':
          condition = '包含';
          break;
        case 'select':
          condition = '等于';
          break;
        case 'multipleselect':
          condition = '等于';
          break;
        case 'startdate':
          condition = '大于';
          break;
        case 'enddate':
          condition = '小于';
          break;
        default:
          condition = '';
      }
      return condition;
    };

    const selectFilterName = (index, $event) => {
      props.filterRule.forEach((v) => {
        if (v.name === $event) {
          filterArray.value[index].path = v.path;
          filterArray.value[index].type = v.type;
          filterArray.value[index].value = null;
          filterArray.value[index].condition = filterCondition(v.type);
          filterArray.value[index].options = v?.options;
          filterArray.value[index].cb = v?.cb || (() => {});
        }
      });
    };

    // 筛选
    const confirmFilter = () => {
      showPopover.value = false;
      context.emit('filterchange', filterArray.value);
    };

    // 是否可添加筛选条件
    const addFlag = computed(() => {
      return filterArray.value.length < props.filterRule.length;
    });

    // 可选择的筛选条件
    const filterOption = computed(() => {
      let option = [];

      props.filterRule.forEach((v) => {
        let isExist = false;
        filterArray.value.forEach((v2) => {
          if (v.name === v2.name) {
            isExist = true;
          }
        });
        if (!isExist) {
          option.push({
            label: v.name,
            value: v.name
          });
        }
      });

      return option;
    });

    const clickAdd = () => {
      if (addFlag.value) {
        filterArray.value.push({
          name: '',
          type: '',
          value: null
        });
      }
    };

    return {
      showPopover,
      clickFilter,
      handleClose,
      clickAdd,
      clickDelete,
      filterArray,
      filterOption,
      addFlag,
      clickReset,
      filterCondition,
      selectFilterName,
      confirmFilter,
      clickOutside
    };
  }
};
</script>

<style lang="less" scoped>
.filterWrap {
  display: flex;
  align-items: center;
  width: 50px;
  justify-content: center;
  cursor: pointer;
}

.selectLine {
  display: flex;
  align-items: center;
  margin: 5px 0;

  .item {
    margin: 0 5px;
  }

  .circleNumber {
    border: 1px solid #2c7ef8;
    border-radius: 50%;
    color: #2c7ef8;
    display: block;
    font-size: 14px;
    height: 32px;
    width: 32px;
    line-height: 32px;
    text-align: center;
  }

  .filterName {
    width: 150px;
  }

  .filterCondition {
    width: 120px;
  }

  .filterValue {
    width: 400px;
  }

  .filterDelete {
    cursor: pointer;
    &:hover {
      color: red;
    }
  }
}

.addBtn {
  display: flex;
  justify-content: left;
  align-items: center;
  color: #2c7ef8;
  cursor: pointer;
  margin-top: 20px;
  width: 50px;
}

.notAllowed {
  cursor: not-allowed;
}

.btnWrap {
  display: flex;
  justify-content: space-between;

  .btn {
    margin: 0 5px;
  }
}
</style>
