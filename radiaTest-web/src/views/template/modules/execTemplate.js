import { h } from 'vue';
import axios from '@/axios';
import { NSelect } from 'naive-ui';

const postExecData = (row) => {
  axios.post('/v1/job/template', {
    id: row.id,
    frame: row.frame,
  })
    .then((res) => {
      if (res.error_code === 200) {
        window.$notification?.success({
          content: '测试任务已执行完成',
          meta: `模板：${row.name}`,
        });
        row.frame = null;
      }
    })
    .catch((err) => {
      if (!err.message && !err.data.validation_error) {
        window.$message?.error('发生未知错误，执行失败，请联系管理员进行处理');
      } else if (err.data.validation_error) {
        window.$message?.error(err.data.validation_error.body_params[0].msg);
      } else {
        window.$message?.error(err.message);
      }
      row.frame = null;
    });
};

const handleExecute = async (row, dOccupy) => {
  return new Promise((resolve) => {
    new Promise((resolveWaitSend) => setTimeout(resolveWaitSend, 1000))
      .then(() => {
        dOccupy.content = '执行请求已发送';
        postExecData(row);
        window.$message?.success('模板已成功执行，请前往测试看板查看');
        resolve();
      });
  });
};

const handlePositiveClick = (row, dOccupy) => {
  dOccupy.loading = true;
  return handleExecute(row, dOccupy);
};

const renderExecute = (row) => {
  return h('div', {}, [
    h(
      'p',
      {
        style: {
          fontSize: '18px',
          fontWeight: '500',
        },
      },
      `待执行模板:  ${row.name}`
    ),
    h(
      'p',
      {
        style: {
          height: '20px',
        },
      },
      '环境架构'
    ),
    h(NSelect, {
      value: row.frame,
      onUpdateValue: (value) => { row.frame = value; },
      options: [
        {
          label: 'aarch64',
          value: 'aarch64'
        },
        {
          label: 'x86_64',
          value: 'x86_64'
        },
      ],
      placeholder: '请选择架构',
    }),
  ]);
};

const handleExecClick = (row) => {
  const dOccupy = window.$dialog?.info({
    title: '确定要执行该模板吗？',
    content: () => renderExecute(row),
    negativeText: '取消',
    positiveText: '确认',
    onPositiveClick: () => handlePositiveClick(row, dOccupy),
  });
};

export {
  handleExecClick,
};
