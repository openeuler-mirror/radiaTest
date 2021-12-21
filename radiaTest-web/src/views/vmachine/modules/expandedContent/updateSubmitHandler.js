import { h } from 'vue';
import { NIcon } from 'naive-ui';
import { ArrowRight16Filled as Right } from '@vicons/fluent';

const handleSuccessSubmit = (title, target, data) => {
  return {
    content: `${title + target}已修改`,
    meta: () => {
      return h(
        'div',
        {
          verticalAlign: 'middle'
        },
        data.map((item) => [
          h(
            'div',
            {
              display: 'inline-block'
            },
            `${item.name}: `,
          ),
          h(
            'div',
            {
              display: 'inline-block'
            },
            item.curData,
          ),
          h(
            NIcon,
            {
              display: 'inline-block',
            },
            Right,
          ),
          h(
            'div',
            {
              display: 'inline-block'
            },
            item.newData,
          ),
        ])
      );
    },
  };
};

const handleFailureSubmit = (title, target, mesg) => {
  return {
    content: `${title + target}修改失败`,
    meta: () => {
      return h(
        'div', null, `原因：${mesg}`
      );
    }
  };
};

export {
  handleSuccessSubmit,
  handleFailureSubmit,
};
