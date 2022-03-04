<template>
  <n-button @click="handleCheck">test</n-button>
  <n-button @click="handleAdd">add</n-button>
  <n-button @click="handleRemove">remove</n-button>
  <n-button @click="handleAddRole">addRole</n-button>
</template>

<script>
import { defineComponent, getCurrentInstance } from 'vue';

export default defineComponent({
  setup() {
    const { proxy } = getCurrentInstance();

    return {
      handleCheck() {
        proxy.$axios
          .get('/v1/test')
          .then((res) => {
            window.$message?.info(res.data);
          })
          .catch((err) => window.$message?.error(err.data.error_msg));
      },
      handleAdd() {
        proxy.$axios
          .post('/v1/test', {uri: '/api/v1/test', act: 'GET', eft: 'allow', dom: 'test'})
          .then((res) => {
            window.$message?.info(res.data);
          })
          .catch((err) => window.$message?.error(err.data.error_msg));
      },
      handleRemove() {
        proxy.$axios
          .delete('v1/test', {uri: '/api/v1/test', act: 'GET', eft: 'allow', dom: 'test'})
          .then((res) => {
            window.$message?.info(res.data);
          })
          .catch((err) => window.$message?.error(err.data.error_msg));
      },
      handleAddRole() {
        proxy.$axios
          .post('/v1/test/role')
          .then((res) => {
            window.$message?.info(res.data);
          })
          .catch((err) => window.$message?.error(err.data.error_msg));
      }
    };
  },
});
</script>
