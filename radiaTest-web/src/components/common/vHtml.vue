<template>
  <div class="vhtml" v-html="domString"></div>
</template>

<script>
import { defineComponent } from 'vue';

export default defineComponent({
  props: {
    domString: String,
  }
});
</script>

<style scoped>
.vhtml {
  font-size: 18px;
}
</style>
