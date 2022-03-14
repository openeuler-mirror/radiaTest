import { h, ref } from 'vue';
import { NInput, NDatePicker, NAutoComplete } from 'naive-ui';
import axios from '@/axios';
import { any2stamp, any2standard } from '@/assets/utils/dateFormatUtils';
import { getDesOptions } from '@/assets/utils/formUtils';
import { storage } from '@/assets/utils/storageUtils';

class ConnectState {
  constructor(data) {
    this.originData = data;
    this.formValue = ref(data);
    this.datetime = ref(undefined);
    data.end_time
      ? this.datetime.value = any2stamp(data.end_time)
      : 0;
  }
  update(newData) {
    this.formValue.value = newData;
    this.datetime.value = any2stamp(newData.end_time);
  }
  clean() {
    this.formValue.value = this.originData;
    this.datetime.value = undefined;
  }
  updateDatetime(value) {
    this.datetime.value = value;
  }
  updateDescription = (value) => {
    this.formValue.value.description = value;
  }
  updateListen(value) {
    this.formValue.value.listen = value;
  }
  listenText() {
    if (this.formValue.value.description === 'as the host of ci') {
      return h(
        'p',
        {
          style: {
            height: '20px',
          },
        },
        '请设置worker服务监听的端口号'
      );
    }
    return null;
  }
  listenElement() {
    if (this.formValue.value.description === 'as the host of ci') {
      return h(NInput, {
        placeholder: 'worker监听端口',
        defaultValue: this.formValue.value.listen,
        onUpdateValue: (value) => this.updateListen(value),
      });
    }
    return null;
  }
  datePickerElement() {
    if (
      this.formValue.value.description !== 'as the host of ci' &&
      this.formValue.value.description !== 'used for ci') {
      return h(NDatePicker, {
        onUpdateValue: (value) => this.updateDatetime(value),
        type: 'datetime',
        actions: ['clear', 'now', 'confirm'],
        defaultValue: this.datetime.value,
        isDateDisabled: (ts) => {
          const now = new Date();
          const date = new Date(ts);
          return date <= now - (24 * 60 * 60 * 1000);
        },
        isTimeDisabled: (ts) => {
          const now = new Date();
          const date = new Date(ts);
          if (date.getDate() === now.getDate()) {
            return {
              isHourDisabled: (hour) => hour < now.getHours(),
              isMinuteDisabled: (minute) => minute < now.getMinutes(),
              isSecondDisabled: (second) => second < now.getSeconds(),
            };
          }
          return false;
        },
      });
    }
    return null;
  }
  datePickerText() {
    if (
      this.formValue.value.description !== 'as the host of ci' &&
      this.formValue.value.description !== 'used for ci') {
      return h(
        'p',
        {
          style: {
            height: '20px',
          },
        },
        '请选择释放时间'
      );
    }
    return null;
  }
}

const handleSendRequest = (dOccupy, connect) => {
  dOccupy.content = '占用请求已发送';
  if (connect.formValue.value.description === 'used for ci') {
    return axios.put('/v1/pmachine', {
      id: connect.formValue.value.id,
      description: connect.formValue.value.description,
      occupier: storage.getValue('gitee_name'),
      state: 'occupied',
    });
  } else if (connect.formValue.value.description !== 'as the host of ci') {
    return axios.put('/v1/pmachine', {
      id: connect.formValue.value.id,
      description: connect.formValue.value.description,
      end_time: any2standard(connect.datetime.value),
      occupier: storage.getValue('gitee_name'),
      state: 'occupied',
    });
  }
  return axios.put('/v1/pmachine', {
    id: connect.formValue.value.id,
    description: connect.formValue.value.description,
    listen: connect.formValue.value.listen,
    occupier: storage.getValue('gitee_name'),
    state: 'occupied',
  });
};

const handleOccupy = async (dOccupy, connect) => {
  return new Promise((resolve) => {
    new Promise((resolveWaitSend) => setTimeout(resolveWaitSend, 1000))
      .then(() => handleSendRequest(dOccupy, connect))
      .then((res) => {
        if (res.error_code === '2000') {
          dOccupy.content = '物理机已成功占用';
          return new Promise((resolveWaitResv) =>
            setTimeout(() => {
              resolveWaitResv();
            }, 2 * 1000)
          );
        }
        return Promise.reject(new Error('请检查参数或检查该物理机是否存在'));
      })
      .catch((err) => {
        console.log(err);
        if (!err.message && !err.data.validation_error) {
          window.$message?.error('发生未知错误，请联系管理员进行处理');
        } else if (err.data.validation_error) {
          window.$message?.error(err.data.validation_error.body_params[0].msg);
        } else {
          window.$message?.error(err.message);
        }
        connect.clean();
      })
      .then(resolve);
  });
};

const handleRelease = async (dRelease, connect) => {
  return new Promise((resolve) => {
    new Promise((resolveWaitSend) => setTimeout(resolveWaitSend, 1000))
      .then(() => {
        dRelease.content = '释放请求已发送';
        return axios.put('/v1/pmachine', {
          id: connect.formValue.value.id,
          state: 'idle',
        });
      })
      .then((res) => {
        if (res.error_code === '2000') {
          dRelease.content = '物理机已确认释放';
          return new Promise((resolveWaitResv) =>
            setTimeout(() => {
              resolveWaitResv();
            }, 2 * 1000)
          );
        }
        return Promise.reject(new Error('请检查参数或检查该物理机是否存在'));
      })
      .catch((err) => {
        if (!err.message && !err.data.validation_error) {
          window.$message?.error('发生未知错误，请联系管理员进行处理');
        } else if (err.data.validation_error) {
          window.$message?.error(err.data.validation_error.body_params[0].msg);
        } else {
          window.$message?.error(err.message);
        }
        connect.clean();
      })
      .then(resolve);
  });
};

const handlePositiveClick = (dOccupy, connect) => {
  dOccupy.loading = true;
  return handleOccupy(dOccupy, connect);
};

const renderOccupy = (connect) => {
  return h('div', {}, [
    h(
      'p',
      {
        style: {
          fontSize: '18px',
          fontWeight: '500',
        },
      },
      `MAC地址:  ${connect.formValue.value.mac}`
    ),
    h(
      'p',
      {
        style: {
          height: '20px',
        },
      },
      '使用说明'
    ),
    h(NAutoComplete, {
      value: connect.formValue.value.description,
      onUpdateValue: connect.updateDescription,
      options: getDesOptions(connect.formValue),
      placeholder: '请输入使用说明',
    }),
    connect.listenText(),
    connect.listenElement(),
    connect.datePickerText(),
    connect.datePickerElement(),
  ]);
};

const handleConnectClick = (connect, type) => {
  if (type === 'occupy') {
    const dOccupy = window.$dialog?.info({
      title: '确定要占用该机器吗？',
      content: () => renderOccupy(connect),
      negativeText: '取消',
      positiveText: '确认',
      onPositiveClick: () => handlePositiveClick(dOccupy, connect),
    });
  } else {
    const dRelease = window.$dialog?.info({
      title: '确定要释放该机器吗？',
      content: `MAC地址:  ${connect.formValue.value.mac}`,
      negativeText: '取消',
      positiveText: '确认',
      onPositiveClick: () => {
        dRelease.loading = true;
        return handleRelease(dRelease, connect);
      },
    });
  }
};

export {
  ConnectState,
  handleConnectClick,
};
