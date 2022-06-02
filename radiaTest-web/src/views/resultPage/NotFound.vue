<template>
  <div class="main">
    <n-result
      title="404 资源不存在"
      description="抱歉，暂时无法找到该页面"
    >
      <template #icon>
        <img
          style="width: 800px;"
          src="/pageNotFound.png"
        />
      </template>
      <template #footer>
        <n-button
          @click="handleBackHome"
        >
          返回首页
        </n-button>
      </template>
    </n-result>
  </div>
</template>

<script>
import { defineComponent } from 'vue';
import { useRouter } from 'vue-router';

export default defineComponent({
  setup() {
    const router = useRouter();

    return {
      handleBackHome() {
        router.push('/home');
      },
    };
  },
});
</script>

<style scoped>
.main {
  height: 100%;
}
</style>
