import { ref } from 'vue';

const icon = ref(null);

const handleEnter = () => {
  icon.value.rotate();
};

const handleLeave = () => {
  icon.value.reverse();
};

export default {
  icon,
  handleEnter,
  handleLeave,
};
