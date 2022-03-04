<template>
  <n-modal
    v-model:show="showModal"
    preset="dialog"
    title="Dialog"
    :showIcon="false"
    :mask-closable="false"
  >
    <template #header>
      <div>添加用户</div>
    </template>
    <div style="display: flex">
      <n-input v-model:value="name" placeholder="请输入用户名"></n-input>
      <n-button type="primary" @click="searchUser">添加</n-button>
    </div>
    <div style="height: 200px; padding: 5px; overflow-y: auto">
      <p style="font-size: 14px">已选用户:</p>
      <delete-item
        @deleteItem="deleteItems(index)"
        v-for="(item, index) in usersList"
        :key="index"
        style="text-align: center; width: 80px; margin: 3px"
      >
        <n-avatar round size="small" :src="item.avatar_url" />
        <p style="max-width: 80px">
          <n-ellipsis style="max-width: 80px">
            {{ item.gitee_name }}
          </n-ellipsis>
        </p>
      </delete-item>
    </div>
    <template #action>
      <n-space style="width: 100%">
        <n-button type="error" ghost size="large" @click="close">
          取消
        </n-button>
        <n-button size="large" @click="submit" type="primary" ghost>
          提交
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>
<script>
import deleteItem from '@/components/common/deleteItem.vue';
export default {
  components: { deleteItem },
  props: ['userList'],
  data() {
    return {
      showModal: false,
      name: ''
    };
  },
  methods: {
    deleteItems(index) {
      this.$emit('deleteUser', index);
    },
    searchUser() {
      this.$emit('search', this.name);
    },
    close() {
      this.showModal = false;
    },
    open() {
      this.showModal = true;
    },
    submit() {
      this.$emit('submit');
      this.close();
    }
  }
};
</script>
