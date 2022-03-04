import { ref } from 'vue';
import axios from '@/axios';
import { getRules } from './ruletable';
const createRef = ref();
const formType = ref('create');
const editData = ref();
function setFormType(type) {
  formType.value = type;
}
function setEditData(data) {
  editData.value = data;
}
function createRule() {
  setFormType('create');
  createRef.value.show();
}
function submitForm({ data, type }) {
  if (type === 'create') {
    axios
      .post('/v1/scope', data)
      .then(() => {
        getRules();
      })
      .catch((err) => window.$message?.error(err.data.error_msg || '未知错误'));
  } else {
    axios
      .put(`/v1/scope/${data.id}`, data)
      .then(() => {
        getRules();
      })
      .catch((err) => window.$message?.error(err.data.error_msg || '未知错误'));
  }
}
export {
  editData,
  formType,
  createRef,
  createRule,
  submitForm,
  setFormType,
  setEditData,
};
