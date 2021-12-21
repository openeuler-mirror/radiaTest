<template>
  <div class="normal-menu">
    <h2>{{ title }}</h2>
    <p
      :id="item.text"
      class="sub"
      v-for="item in sub"
      :key="item.id"
      :style="{
        color: printColor(item.disabled),
      }"
      @mouseenter="handleHover(item.text, item.disabled)"
      @mouseleave="handleLeave(item.text, item.disabled)"
      @click="
        () => {
          if (!item.disabled) {
            return handleClick(item.url);
          }
        }
      "
    >
      {{ item.text }}
    </p>
  </div>
</template>

<script>
import { defineComponent } from 'vue';
import { useRouter } from 'vue-router';

export default defineComponent({
  props: {
    title: {
      type: String,
      default: '默认标题',
    },
    sub: Array,
  },
  setup () {
    const router = useRouter();
    return {
      printColor (disabled) {
        if (!disabled) {
          return 'black';
        }
        return 'grey';

      },
      handleHover (id, disabled) {
        if (!disabled) {
          document.getElementById(id).style.cursor = 'pointer';
          document.getElementById(id).style.backgroundColor =
            'rgba(0, 47, 167, 1)';
          document.getElementById(id).style.color = 'white';
        } else {
          document.getElementById(id).style.cursor = 'not-allowed';
        }
      },
      handleLeave (id, disabled) {
        if (!disabled) {
          document.getElementById(id).style.backgroundColor = 'white';
          document.getElementById(id).style.color = 'black';
        } else {
          document.getElementById(id).style.color = 'grey';
        }
      },
      handleClick (url) {
        router.push(url);
      },
    };
  },
});
</script>

<style scoped>
.normal-menu {
  display: inline-grid;
  width: 200px;
  padding: 10px 50px;
  text-align: center;
}
.sub {
  font-size: 20px;
  margin: 0px;
  padding: 10px;
}
.sub:hover {
  cursor: pointer;
}
</style>
