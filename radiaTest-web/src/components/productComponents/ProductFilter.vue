<template>
  <n-input-group @input="handleGroupInput">
    <n-input
      v-model:value="name"
      :style="{ width: '12%' }"
      round
      placeholder="产品名称"
    />
    <n-input
      v-model:value="version"
      :style="{ width: '12%' }"
      placeholder="版本名称"
    />
    <n-input
      v-model:value="description"
      :style="{ width: '36%' }"
      placeholder="描述信息"
    />
    <clear-input @clearAll="clearAll" />
  </n-input-group>
</template>

<script>
import { ref, watch, defineComponent } from 'vue';
import { useStore } from 'vuex';

import ClearInput from '@/components/CRUD/ClearInput.vue';

export default defineComponent({
  components: {
    ClearInput,
  },
  setup() {
    const store = useStore();
    const name = ref('');
    const version = ref('');
    const description = ref('');

    const clearAll = () => {
      name.value = '';
      version.value = '';
      description.value = '';
      store.commit('filterProduct/setName', name.value);
      store.commit('filterProduct/setVersion', version.value);
      store.commit('filterProduct/setDescription', description.value);
    };

    watch([name, version, description], () => {
      store.commit('filterProduct/setName', name.value);
      store.commit('filterProduct/setVersion', version.value);
      store.commit('filterProduct/setDescription', description.value);
    });

    return {
      name,
      version,
      description,
      clearAll,
    };
  },
});
</script>

<style scoped></style>
