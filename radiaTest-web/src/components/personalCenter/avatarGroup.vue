<template>
  <n-avatar-group :options="props.options" :size="size" :max="max">
    <template #avatar="{ option: { name, src } }">
      <n-tooltip>
        <template #trigger>
          <n-avatar :src="src" />
        </template>
        {{ name }}
      </n-tooltip>
    </template>
    <template #rest="{ options: restOptions, rest }">
      <n-dropdown :options="createDropdownOptions(restOptions)" placement="top">
        <n-avatar :style="{ backgroundColor: '#cccccc' }">+{{ rest }}</n-avatar>
      </n-dropdown>
    </template>
  </n-avatar-group>
</template>

<script setup>
const props = defineProps(['options', 'size', 'max']);

const createDropdownOptions = (options) =>
  options.map((option) => ({
    key: option.name,
    label: option.name
  }));
</script>

<style lang="less"></style>
