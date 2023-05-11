<template>
  <n-card
    :bordered="false"
    size="huge"
    content-style="padding:5px 50px"
    :segmented="{
      content: 'hard'
    }"
    style="height: 100%"
    header-style="
            font-size: 30px;
            height: 80px;
            font-family: 'v-sans';
            padding-top: 40px;
            background-color: rgb(242,242,242);
        "
  >
    <template #default>
      <n-tabs
        animated
        type="card"
        size="large"
        tab-style="width: 200px"
        @update:value="changeView"
        v-model:value="tabValue"
      >
        <n-tab name="automatic">自动化测试</n-tab>
        <n-tab name="manual">手工测试</n-tab>
        <n-tab name="gui" :disabled="true">GUI测试</n-tab>
      </n-tabs>
      <router-view></router-view>
    </template>
  </n-card>
</template>

<script setup>
const router = useRouter();
const tabValue = ref('');

const changeView = (name) => {
  router.push({ name });
};

onMounted(() => {
  tabValue.value = router.currentRoute.value.name;
});
</script>

<style scoped lang="less">
.nav-header {
  display: flex;
  align-items: center;
}

.nav-body {
  position: relative;
  white-space: nowrap;
  z-index: 1;
  display: -ms-flexbox;
  display: -webkit-box;
  display: flex;
  -ms-flex-pack: center;
  -webkit-box-pack: center;
  justify-content: center;

  .nav-wrapper {
    position: relative;
    border: none;
    list-style-type: none;
    padding: 0;

    li {
      list-style: none;
      float: left;
      z-index: 2;
      padding: 0 20px;

      a {
        display: inline-block;
        position: relative;
        margin: 0;
        color: #383838;
        font-size: 15px;
        font-weight: 400;
        cursor: pointer;
        border-bottom: 3px solid #fafafa;

        &.active {
          border-bottom: 3px solid #3da8f5;
        }
      }
    }
  }
}
</style>
