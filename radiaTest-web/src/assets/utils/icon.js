import { NIcon } from 'naive-ui';
import { h } from 'vue';

function renderIcon(icon) {
  return () =>
    h(
      NIcon,
      { color: 'rgba(0, 47, 167, 1)' },
      {
        default: () => h(icon),
      }
    );
}
export { renderIcon };
