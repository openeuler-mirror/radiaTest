<template>
  <div :style="{ fontSize: fontsize + 'px' }">
    <template v-for="(item, index) in list" :key="index">
      <span :class="[index !== list.length - 1 ? 'item' : 'activeItem']">
        {{ item }}
      </span>
      <span v-if="index !== list.length - 1" class="item">
        {{ separator }}
      </span>
    </template>
  </div>
</template>
<script>
export default {
  props: {
    fontsize: {
      type: Number,
      default: 16,
    },
    list: Array,
    separator: {
      type: String,
      default: '/',
    },
  },
};
</script>
<style scoped>
.item {
  color: #ccc;
  margin: 0 5px;
}
.activeItem {
  color: #000;
}
</style>
