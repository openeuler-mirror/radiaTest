<template>
  <div :id="vncToken" class="novnc-viewer"></div>
</template>

<script>
import RFB from '@novnc/novnc/core/rfb';
import { useMessage } from 'naive-ui';
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';
import { getMachineGroupDetails } from '@/api/get';
import router from '@/router';
// import settings from '@/assets/config/settings.js';

export default defineComponent({
  props: {
    websockifyListen: Number,
    vncToken: String,
  },
  setup(props) {
    const rfb = ref(null);
    const message = useMessage();
    const url = ref(
      `ws://${props.ip}:${props.websockifyListen}?token=${props.vncToken}`
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
      const group = await getMachineGroupDetails(router.currentRoute.value.params.machineId);
      const groupId = group.data.messenger_ip;
      url.value = `ws://${groupId}:${props.websockifyListen}?token=${props.vncToken}`;
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
