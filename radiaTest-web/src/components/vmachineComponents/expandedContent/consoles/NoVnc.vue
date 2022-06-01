<template>
  <div :id="vncToken" class="novnc-viewer"></div>
</template>

<script>
import RFB from '@novnc/novnc/core/rfb';
import settings from '@/assets/config/settings.js';
import { useMessage } from 'naive-ui';
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';

export default defineComponent({
  props: {
    websockifyIp: String,
    websockifyListen: Number,
    vncToken: String,
  },
  setup(props) {
    const rfb = ref(null);
    const message = useMessage();
    const url = ref(
      `${settings.websocketProtocol}://${props.websockifyIp}:${props.websockifyListen}?token=${props.vncToken}`
    );

    const connectedToServer = () => {
      message.success('连接VNC服务成功');
    };

    const connectVnc = () => {
      let newRfb = new RFB(document.getElementById(props.vncToken), url.value);
      newRfb.addEventListener('connect', connectedToServer);
      newRfb.scaleViewport = true;
      newRfb.resizeSession = true;
      rfb.value = newRfb;
    };

    onMounted(async () => {
      connectVnc();
    });

    onUnmounted(() => {
      rfb.value.disconnect();
    });

    return {};
  },
});
</script>

<style scoped>
.novnc-viewer {
  height: 800px;
  width: 100%;
  background-color: black;
}
</style>
