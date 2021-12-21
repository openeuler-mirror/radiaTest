import { ref } from 'vue';
import createForm from './createForm';
import updateForm from './updateForm';

const createFormRef = ref(null);
const createModalRef = ref(null);
const updateFormRef = ref(null);
const updateModalRef = ref(null);

const data = ref({
  iso: {
    x64: {
      id: null,
      url: '',
      ks: '',
      efi: '',
      location: '',
    },
    aarch64: {
      id: null,
      url: '',
      ks: '',
      efi: '',
      location: '',
    },
  },
  qcow2: {
    x64: {
      id: null,
      url: '',
      user: '',
      port: '',
      password: '',
    },
    aarch64: {
      id: null,
      url: '',
      user: '',
      port: '',
      password: '',
    },
  },
});

const handleCreateClick = (milestoneId, filetype, frame) => {
  createForm.thisFiletype.value = filetype;
  createForm.formValue.value.milestone_id = milestoneId,
  createForm.formValue.value.frame = frame;
  createModalRef.value.show();
};
  
const handleUpdateClick = (milestoneId, filetype, frame) => {
  updateForm.thisFiletype.value = filetype;
  let _frame = 'aarch64';
  frame === 'x86_64' ? _frame = 'x64' : 0;
  updateForm.formValue.value = JSON.parse(
    JSON.stringify(data.value[filetype][_frame])
  );
  updateForm.formValue.value.milestone_id = milestoneId;
  updateForm.formValue.value.frame = frame;
  updateModalRef.value.show();
};

const clean = () => {
  data.value = {
    iso: {
      x64: {
        id: null,
        url: '',
        ks: '',
        efi: '',
        location: '',
      },
      aarch64: {
        id: null,
        url: '',
        ks: '',
        efi: '',
        location: '',
      },
    },
    qcow2: {
      x64: {
        id: null,
        url: '',
        user: '',
        port: '',
        password: '',
      },
      aarch64: {
        id: null,
        url: '',
        user: '',
        port: '',
        password: '',
      },
    },
  };
};

export default {
  createFormRef,
  createModalRef,
  updateModalRef,
  updateFormRef,
  data,
  clean,
  handleCreateClick,
  handleUpdateClick,
};

