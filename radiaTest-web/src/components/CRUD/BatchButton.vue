<template>
  <n-button
    :type="type"
    size="large"
    :disabled="disabled"
    round
  >
    <slot name="icon"></slot>
    批量{{ text }}
  </n-button>
</template>

<script>
import { ref, watch, computed, defineComponent } from 'vue';
import { useStore } from 'vuex';

export default defineComponent({
  props: {
    text: String,
    type: String,
  },
  setup() {
    const disabled = ref(true);
    const store = useStore();
    const selectedData = computed(() => store.getters.selectedData);
    const deletedData = computed(() => store.getters.deletedData);
    watch([selectedData, deletedData], () => {
      if (selectedData.value.length - deletedData.value.length === 0) {
        disabled.value = true;
      } else {
        disabled.value = false;
      }
    });
    return {
      disabled,
    };
  },
});
</script>

<style scoped></style>
