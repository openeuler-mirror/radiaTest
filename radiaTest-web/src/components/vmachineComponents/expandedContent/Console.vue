<template>
  <div id="console-container">
    <no-vnc
      :websockify-ip="data.machine_group.websockify_ip"
      :websockify-listen="data.machine_group.websockify_listen"
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
