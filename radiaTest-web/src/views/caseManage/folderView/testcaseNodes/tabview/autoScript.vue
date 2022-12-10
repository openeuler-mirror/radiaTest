<template>
  <n-code :code="code" language="bash" />
</template>

<script>
import {  defineComponent } from 'vue';

export default defineComponent({
  props:['code'],
  setup() {
  },
});
</script>

<style scoped></style>
