import { ref } from 'vue';
const userList = ref([]);
const userModal = ref();
function addUser() {
  userModal.value.open();
}
function searchUser(name) {
  console.log(name);
}

export { userList, userModal, addUser, searchUser };
