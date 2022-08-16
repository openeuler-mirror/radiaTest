<template>
  <n-popover
    trigger="manual"
    placement="bottom"
    :disabled="isDisabled"
    :show="showPopover"
    @clickoutside="clickoutside"
  >
    <template #trigger>
      <n-button text @click="clickTrigger">
        {{ triggerValue?.join() || '无' }}
      </n-button>
    </template>
    <div class="select-box-warp">
      <div class="search-content">
        <n-input v-model:value="inputValue" type="text" placeholder="搜索" @input="search">
          <template #suffix>
            <n-icon>
              <Search />
            </n-icon>
          </template>
        </n-input>
      </div>
      <div class="selectable-selection">
        <n-scrollbar style="max-height: 300px">
          <ul v-if="!multiple">
            <li class="select-item" v-for="(item, index) in selectArrayTemp" :key="index" @click="singleSelect(item)">
              <div class="item-content-wrap">
                <div class="item-name">{{ item.label }}</div>
              </div>
            </li>
          </ul>
          <ul v-else>
            <n-checkbox-group v-model:value="groupValue">
              <div v-for="(item, index) in selectArrayTemp" :key="index" class="select-item">
                <n-checkbox :value="item" :label="item.label"></n-checkbox>
              </div>
            </n-checkbox-group>
          </ul>
        </n-scrollbar>
      </div>
      <n-divider style="margin: 4px 0" />
      <div class="footer" v-show="multiple">
        <n-button type="info" @click="confirm" class="btn">确定</n-button>
      </div>
    </div>
  </n-popover>
</template>

<script>
import { Search } from '@vicons/ionicons5';

export default {
  components: {
    Search
  },
  props: ['isDisabled', 'multiple', 'defaultValue', 'selectArray'],
  data() {
    return {
      showPopover: false,
      selectArrayTemp: [],
      inputValue: null,
      groupValue: null,
      triggerValue: ['无']
    };
  },
  methods: {
    clickTrigger() {
      this.showPopover = true;
    },
    clickoutside() {
      this.showPopover = false;
    },
    singleSelect(item) {
      this.triggerValue = [item.label];
      this.$emit('updateValue', item.value);
      this.showPopover = false;
    },
    confirm() {
      this.triggerValue = this.groupValue?.map((item) => {
        return item.label;
      });
      this.$emit('updateValue', this.groupValue);
      this.showPopover = false;
    },
    search() {
      if (this.inputValue) {
        this.selectArrayTemp = this.selectArray.filter((item) => {
          return item.label.indexOf(this.inputValue) > -1;
        });
      } else {
        this.selectArrayTemp = this.selectArray;
      }
    }
  },
  mounted() {
    this.selectArrayTemp = this.selectArray;
    this.triggerValue = this.defaultValue;
  }
};
</script>

<style lang="less" scoped>
ol,
ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.selectable-selection {
  padding: 10px 0;

  .select-item {
    padding: 6px 16px;
    cursor: pointer;
    &:hover {
      background-color: #f7f7f7;
    }

    .item-name {
      color: #383838;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
}

.footer {
  display: flex;
  justify-content: center;

  .btn {
    width: 85%;
  }
}
</style>
