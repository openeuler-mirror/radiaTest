<template>
  <n-avatar-group :options="props.data" :size="props.size" :max="props.max">
    <template #avatar="{ option: { gitee_name, avatar_url } }">
      <n-tooltip>
        <template #trigger>
          <n-avatar :src="avatar_url" />
        </template>
        {{ gitee_name }}
      </n-tooltip>
    </template>
    <template #rest="{ options: restOptions, rest }">
      <n-tooltip>
        <template #trigger>
          <n-avatar>+{{ rest }}</n-avatar>
        </template>
        <span class="rest-username" v-for="(item, index) in restOptions" :key="index">
          {{ item.gitee_name }}
        </span>
      </n-tooltip>
    </template>
  </n-avatar-group>
</template>

<script setup>
const props = defineProps({
  data: {
    type: Array,
    default: () => [],
  },
  size: {
    type: Number,
    default: () => 40,
  },
  max: {
    type: Number,
    default: () => 3,
  },
});
</script>

<style scoped lang="less">
.rest-username {
  margin: 0 4px 0 4px;
}
</style>
