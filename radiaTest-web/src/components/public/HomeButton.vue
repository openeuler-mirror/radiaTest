<template>
  <div ref="button" class="homeButton" @click="handleClick"><slot></slot></div>
</template>

<script>
import { ref, computed, onMounted, defineComponent } from 'vue';

export default defineComponent({
  props: {
    invertColor: {
      type: Boolean,
      default: false,
    },
  },
  setup(props, context) {
    const button = ref(null);
    onMounted(() => {
      if (computed(() => props.invertColor).value) {
        button.value.style.color = 'rgba(0, 47, 167, 1)';
        button.value.style.backgroundColor = 'white';
        button.value.style.borderColor = 'rgba(0, 47, 167, 1)';
      } else {
        button.value.style.color = 'white';
        button.value.style.backgroundColor = 'rgba(0, 47, 167, 1)';
        button.value.style.borderColor = 'rgba(0, 47, 167, 1)';
      }
    });
    return {
      button,
      handleClick() {
        context.emit('click');
      },
    };
  },
});
</script>

<style scoped>
.homeButton {
  border-radius: 46px;
  border-style: solid;
  border-width: 1px;
  padding: 16px 60px;
  font-size: 30px;
  margin-left: 10px;
  margin-right: 10px;
  transition: box-shadow 0.2s ease-in-out;
}
.homeButton:hover {
  cursor: pointer;
  box-shadow: 5px 5px 10px rgb(152, 152, 152, 1);
}
</style>
