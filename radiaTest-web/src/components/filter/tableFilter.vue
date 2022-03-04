<template>
  <div>
    <n-input-group style="margin: 10px 0">
      <template v-for="(item, index) in filters" :key="index">
        <n-input
          v-if="item.type === 'input'"
          v-model:value="filterValue[item.key]"
          :style="{
            width: item.width || Math.floor(100 / filters.length) + '%',
          }"
          round
          :placeholder="item.placeholder"
          @change="filterChange"
        />
        <n-select
          v-if="item.type === 'select'"
          v-model:value="filterValue[item.key]"
          size="large"
          @update:value="filterChange"
          :style="{
            width: item.width || Math.floor(100 / filters.length) + '%',
          }"
          :placeholder="item.placeholder"
          :options="item.options"
          clearable
        />
      </template>
      <clear-input @clearAll="clearAll" />
    </n-input-group>
  </div>
</template>
<script>
import ClearInput from '@/components/CRUD/ClearInput.vue';
import { ref } from 'vue';
export default {
  components: {
    ClearInput
  },
  methods: {
    filterChange() {
      this.$emit('filterchange', this.filterValue);
    },
    clearAll() {
      const keys = Object.keys(this.filterValue);
      keys.forEach(item => {
        this.filterValue[item] = null;
      });
      this.filterChange();
    }
  },
  props: ['filters'],
  setup(props) {
    const keys = props.filters.map(item => item.key);
    const filterValue = ref({});
    keys.forEach(item => {
      filterValue.value[item] = null;
    });
    return {
      filterValue
    };
  }
};
</script>
