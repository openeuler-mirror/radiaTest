<template>
  <div
    class="deleteBox"
    @mouseover="showIcon=true"
    @mouseleave="showIcon=false"
  >
    <slot></slot>
    <div
      class="mark"
      v-show="showIcon"
    >
      <n-icon
        size="30"
        style="cursor: pointer;"
        @click="deleteItem"
      >
        <delete-outlined />
      </n-icon>
    </div>
  </div>
</template>

<script>
import { DeleteOutlined } from '@vicons/antd';
export default {
  components: {
    DeleteOutlined
  },
  data () {
    return {
      showIcon: false
    };
  },
  methods: {
    deleteItem () {
      this.$emit('deleteItem');
    }
  }
};
</script>

<style>
.deleteBox {
  position: relative;
  display: inline-block;
}

.mark {
  position: absolute;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5) !important;
  left: 0;
  top: 0;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
