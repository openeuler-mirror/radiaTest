<template>
  <n-popover placement="right-start" trigger="hover" :show-arrow="false" raw>
    <template #trigger >
      <slot name="username">
        <span class="sub-content user">{{ userInfo?.gitee_name }}</span>
      </slot>
    </template>
    <n-card>
      <div
        style="display: flex;flex-direction: column;align-items: center;"
      >
        <n-avatar round :size="96" :src="userInfo.avatar_url" />
        <div style="padding-top: 20px">
          <p style="text-align: center">
            <span>{{ userInfo.gitee_name }}</span>
          </p>
          <p style="padding-top: 20px">
            <span>手机：</span>
            <span>{{ userInfo.phone }}</span>
          </p>
          <p>
            <span>邮箱：</span>
            <span>{{ userInfo.cla_email }}</span>
          </p>
        </div>
      </div>
    </n-card>
  </n-popover>
</template>
<script>
export default {
  props: ['userInfo'],
  setup() {},
};
</script>
<style scoped>
.user {
  color: #4ca8ff;
  font-weight: 600;
}
.user:hover {
  cursor: pointer;
}
</style>
