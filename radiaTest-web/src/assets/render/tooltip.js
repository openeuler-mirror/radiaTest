import { h } from 'vue';
import { NTooltip } from 'naive-ui';

const renderTooltip = (trigger, content) => {
  return h(NTooltip, null, {
    trigger: () => trigger,
    default: () => content,
  });
};

export {
  renderTooltip,
};

