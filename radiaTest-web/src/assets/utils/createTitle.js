import { h } from 'vue';
import { NH2, NText } from 'naive-ui';

const createTitle = (title) => {
  return h(
    NH2,
    {
      prefix: 'bar',
      alignText: true,
      color: 'rgba(0, 47, 167, 1)',
      style: 'margin: 0 0 !important;',
    },
    h(
      NText,
      {
        color: 'rgba(0, 47, 167, 1)',
      },
      title
    )
  );
};

export {
  createTitle,
};
