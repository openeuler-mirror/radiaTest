<template>
  <n-card hoverable>
    <n-tree block-line :data="treeData" virtual-scroll style="height: 320px" />
  </n-card>
</template>

<script setup>
const props = defineProps(['data']);
const { data } = toRefs(props);
const treeData = ref([]);

const getChildren = (arr) => {
  return arr?.map((item) => {
    return {
      label: item.name,
      key: `case-${item.id}`
    };
  });
};

const init = () => {
  treeData.value = [];
  for (let item in data.value) {
    treeData.value?.push({
      label: item,
      key: `suite-${item}`,
      children: getChildren(data.value[item].cases)
    });
  }
};

watch(data, () => {
  init();
});

onMounted(() => {
  init();
});
</script>
