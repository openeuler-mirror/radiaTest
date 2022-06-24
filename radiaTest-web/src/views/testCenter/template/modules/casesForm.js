import { ref } from 'vue';

const casesValue = ref([]);
const options = ref([]);
const loading = ref(false);

const clean = () => {
  casesValue.value = [];
  options.value = [];
};

export default {
  casesValue,
  options,
  loading,
  clean,
};
