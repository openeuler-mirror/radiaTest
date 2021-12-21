<template>
  <div>
    <card-page title="用户组管理">
      <userGroupManagement />
    </card-page>
  </div>
</template>
<script>
import userGroupManagement from './userGroupManagement/UserGroupManagement.vue';
import cardPage from '@/components/common/cardPage';

export default {
  components: {
    userGroupManagement, cardPage
  },
  setup () {

  },
};
</script>
