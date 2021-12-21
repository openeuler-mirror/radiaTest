<template>
  <div id="console-container">
    <no-vnc
      :websockify-listen="data.websockify_listen"
      :vnc-token="data.vnc_token"
    />
  </div>
</template>

<script>
import { ref, defineComponent } from 'vue';
import NoVnc from './consoles/NoVnc';

export default defineComponent({
  components: {
    NoVnc,
  },
  props: {
    data: {
      type: Object,
    },
  },
  setup() {
    const vnc = ref(null);
    return {
      vnc,
    };
  },
});
</script>

<style scoped>
#console-container {
  width: 100%;
  text-align: center;
}
</style>
