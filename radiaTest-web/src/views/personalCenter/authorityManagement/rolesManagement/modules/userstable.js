import { ref } from 'vue';
// import axios from '@/axios';
const userList = ref([]);
const userModal = ref();
function addUser() {
  userModal.value.open();
  console.log('add');
}
function searchUser(name) {
  // axios.get()
  console.log(name);
}

export { userList, userModal, addUser, searchUser };
