<template>
  <div></div>
</template>

<script>
import { defineComponent } from 'vue';
import { useRouter } from 'vue-router';

export default defineComponent({
  setup() {
    const router = useRouter();
    router.replace(router.currentRoute.value.query.redirect);
  },
});
</script>

<style scoped></style>
