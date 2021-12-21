<template>
  <div
    ref="animateButton"
    class="animate-button"
    @mouseenter="handleHover"
    @mouseleave="handleLeave"
    @click="handleClick"
    :style="{ width: size + 'px', height: size + 'px' }"
  >
    <slot name="icon"></slot>
    <p ref="text" class="text">
      <slot name="text"></slot>
    </p>
  </div>
</template>

<script>
import { ref, onMounted, defineComponent } from 'vue';
import { useRouter } from 'vue-router';

export default defineComponent({
  props: {
    size: Number,
    url: String,
    disabled: Boolean,
  },
  setup(props, context) {
    const router = useRouter();
    const text = ref(null);
    const animateButton = ref(null);

    onMounted(() => {
      if (props.disabled) {
        animateButton.value.style.color = 'grey';
      } else {
        animateButton.value.style.color = 'black';
      }
    });

    return {
      text,
      animateButton,
      handleClick() {
        if (!props.disabled) {
          router.push(props.url);
          context.emit('out');
        }
      },
      handleHover() {
        if (!props.disabled) {
          animateButton.value.style.cursor = 'pointer';
          animateButton.value.style.boxShadow = '0 0 10px grey';
          animateButton.value.style.color = 'rgba(0, 47, 167, 1)';
        } else {
          animateButton.value.style.cursor = 'not-allowed';
        }
      },
      handleLeave() {
        if (!props.disabled) {
          animateButton.value.style.color = 'black';
          animateButton.value.style.boxShadow = 'none';
        }
      },
    };
  },
});
</script>

<style>
.animate-button {
  display: inline-block;
  text-align: center;
  transition: all 0.4s ease-out;
}
.icon {
  position: relative;
  top: 40px;
}
.text {
  position: relative;
  top: 20px;
  font-size: 20px;
  transition: all 0.4s ease-out;
}
</style>
