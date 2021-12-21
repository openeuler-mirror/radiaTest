<template>
  <n-button
    :type="type"
    size="large"
    :disabled="true"
    @click="handleClick"
    round
  >
    <slot name="icon"></slot>
    批量{{ text }}
  </n-button>
</template>

<script>
import { h, ref, watch, computed, defineComponent } from 'vue';
import { useStore } from 'vuex';
import { useDialog } from 'naive-ui';

export default defineComponent({
  props: {
    text: String,
    type: String,
  },
  setup(props) {
    const dialog = useDialog();
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
      handleClick() {
        const dOcupy = dialog.info({
          title: `确定要批量 ${props.text} 下列机器吗？`,
          content: () =>
            h(
              'div',
              {},
              selectedData.value.map((mac) => h('p', {}, `MAC地址: ${mac}`))
            ),
          negativeText: '取消',
          positiveText: '确认',
          onPositiveClick: () => {
            dOcupy.loading = true;
            return new Promise((resolve) => {
              new Promise((resolveA) => setTimeout(resolveA, 1000))
                .then(() => {
                  dOcupy.content = `${props.text} 请求已发送`;
                  return new Promise((resolveB) =>
                    setTimeout(resolveB, 2 * 1000)
                  );
                })
                .then(() => {
                  dOcupy.content = `物理机已成功 ${props.text}`;
                  return new Promise((resolveC) =>
                    setTimeout(resolveC, 1 * 1000)
                  );
                })
                .then(resolve);
            });
          },
        });
      },
    };
  },
});
</script>

<style scoped></style>
