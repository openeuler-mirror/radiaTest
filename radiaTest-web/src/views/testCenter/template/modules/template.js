import { ref } from 'vue';
import axios from '@/axios';
import { any2standard } from '@/assets/utils/dateFormatUtils';
import { cloneTemplate } from '@/api/post';
import { storage } from '@/assets/utils/storageUtils';

const createModalRef = ref(null);
const createFormRef = ref(null);
const copyButton = ref(null);
const createButton = ref(null);

const personalData = ref([]);
const teamData = ref([]);
const orgnizationData = ref([]);
const taskData = ref([]);

const handleHover = (button) => {
  button.style.cursor = 'pointer';
  button.style.color = 'grey';
};
const handleLeave = (button) => {
  button.style.color = 'rgba(206, 206, 206, 1)';
};

const devideData = (res) => {
  try {
    res.forEach((item) => {
      item.create_time
        ? (item.create_time = any2standard(item.create_time))
        : 0;
      item.update_time
        ? (item.update_time = any2standard(item.update_time))
        : 0;
    });
    personalData.value = res.filter((item) => item.template_type === 'person');
    teamData.value = res.filter((item) => item.template_type === 'group');
    orgnizationData.value = res.filter((item) => item.template_type === 'org');
    taskData.value = res.filter((item) => item.template_type === 'task');
  } catch (error) {
    window.$message?.error(error);
  }
};

const templateList = ref([]);
const getData = () => {
  axios
    .get('/v1/template')
    .then((res) => {
      devideData(res.data);
      templateList.value = res.data.map((item) => ({
        label: item.name,
        value: String(item.id),
      }));
    })
    .catch(() => window.$message?.error('发生未知错误，请联系管理员处理'));
};
const showCloneModal = ref(false);
const cloneForm = ref();
const cloneFormValue = ref({
  cloneTemplateId: undefined,
  permissionType: undefined,
});
const cloneFormRule = {
  cloneTemplateRule: {
    trigger: ['input', 'blur'],
    message: '请选择要克隆的模板',
    validator() {
      if (cloneFormValue.value.cloneTemplateId) {
        return true;
      }
      return false;
    },
  },
  permissionRule: {
    trigger: ['input', 'blur'],
    message: '请选择要克隆的模板',
    validator() {
      if (cloneFormValue.value.permissionType) {
        return true;
      }
      return false;
    },
  },
};
function handleCloneClick() {
  showCloneModal.value = true;
  // const d = window.$dialog?.info({
  //   title: '克隆模板',
  //   showIcon: false,
  //   positiveText: '提交',
  //   negativeText: '关闭',
  //   onNegativeClick: () => {
  //     d.destroy();
  //   },
  //   onPositiveClick: () => {
  //     cloneTemplate({ id: Number(cloneTemplateId.value) }).then(() => {
  //       d.destroy();
  //     });
  //   },
  //   content: () => {
  //     const select = h(NSelect, {
  //       options: templateList.value,
  //       value: cloneTemplateId.value,
  //       onUpdateValue: (value) => {
  //         cloneTemplateId.value = value;
  //       },
  //     });
  //     return h(
  //       NFormItem,
  //       {
  //         rule: cloneTemplateRule,
  //         label: '模板:',
  //       },
  //       select
  //     );
  //   },
  // });
}
function handleCloneSubmit() {
  return new Promise((resolve, reject) => {
    cloneForm.value?.validate((error) => {
      if (!error) {
        cloneTemplate({
          permission_type: cloneFormValue.value.permissionType.split('-')[0],
          creator_id: Number(storage.getValue('gitee_id')),
          org_id: storage.getValue('orgId'),
          group_id: Number(cloneFormValue.value.permissionType.split('-')[1]),
          id: Number(cloneFormValue.value.cloneTemplateId),
        })
          .then(() => {
            resolve();
          })
          .catch((err) => reject(err));
      } else {
        reject(Error('error'));
      }
    });
  });
}

export default {
  cloneForm,
  cloneFormRule,
  templateList,
  cloneFormValue,
  showCloneModal,
  createModalRef,
  createFormRef,
  copyButton,
  createButton,
  personalData,
  teamData,
  orgnizationData,
  taskData,
  handleHover,
  handleLeave,
  devideData,
  getData,
  handleCloneClick,
  handleCloneSubmit,
};
