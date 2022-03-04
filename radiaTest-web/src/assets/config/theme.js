import { ref } from 'vue';

const theme = ref();
function changeTheme(themeParmas) {
  theme.value = themeParmas;
}

export { theme, changeTheme };
