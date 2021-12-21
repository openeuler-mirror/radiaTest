<template>
  <n-popover trigger="hover">
    <template #trigger>
      <n-button
        id="deletePm"
        @click="handleClick"
        :disabled="disabled"
        type="error"
        size="large"
        circle
      >
        <n-icon size="25">
          <delete />
        </n-icon>
      </n-button>
    </template>
    <span>删除所有选中的{{ title }}</span>
  </n-popover>
</template>

<script>
import { ref, watch, computed, defineComponent } from 'vue';
import { useStore } from 'vuex';
import { Delete24Regular as Delete } from '@vicons/fluent';

import { deleteAjax } from '@/assets/CRUD/delete';

export default defineComponent({
  components: {
    Delete,
  },
  props: {
    title: String,
    url: String,
  },
  setup(props) {
    const store = useStore();
    const disabled = ref(true);

    const selectedData = computed(() => store.getters.selectedData);
    const deletedData = computed(() => store.getters.deletedData);
    const realSelectedData = computed(() => {
      return selectedData.value.filter((item) => {
        return !deletedData.value.includes(item);
      });
    });

    watch(realSelectedData, () => {
      if (realSelectedData.value.length === 0) {
        disabled.value = true;
      } else {
        disabled.value = false;
      }
    });
    return {
      disabled,
      ...deleteAjax,
      handleClick: () =>
        deleteAjax.postDelete(
          props.url,
          realSelectedData.value,
          store,
          selectedData
        ),
    };
  },
});
</script>

<style scoped>
.deleteCard {
  max-width: 1000px;
}
</style>
