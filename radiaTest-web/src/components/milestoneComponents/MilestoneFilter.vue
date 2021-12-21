<template>
  <n-input
    size="large"
    v-model:value="value"
    round
    placeholder="搜索里程碑名..."
    clearable
  />
</template>

<script>
import { ref, watch, defineComponent } from 'vue';
import { useStore } from 'vuex';

export default defineComponent({
  setup() {
    const store = useStore();
    const value = ref(null);

    watch(value, () => {
      store.commit('filterValue/setValue', value.value);
    });

    return {
      value,
    };
  },
});
</script>

<style scoped></style>
