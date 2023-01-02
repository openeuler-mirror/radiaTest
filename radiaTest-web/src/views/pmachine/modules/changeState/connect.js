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
    this.datetime = ref();
    if (data.end_time) {
      this.datetime.value = any2stamp(data.end_time);
    } else {
      const oneDay = 1000 * 60 * 60 * 24;
      this.datetime.value = Date.now() + oneDay;
    }
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
  };
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
      this.formValue.value.description !== 'used for ci'
    ) {
      return h(NDatePicker, {
        onUpdateValue: (value) => this.updateDatetime(value),
        type: 'datetime',
        actions: ['clear', 'now', 'confirm'],
        defaultValue: this.datetime.value,
        isDateDisabled: (ts) => {
          const now = new Date();
          const date = new Date(ts);
          const time = 24 * 60 * 60 * 1000;
          return date <= now - time;
        },
        isTimeDisabled: (ts) => {
          const now = new Date();
          const date = new Date(ts);
          if (date.getDate() === now.getDate()) {
            return {
              isHourDisabled: (hour) => hour < now.getHours(),
              isMinuteDisabled: (minute) => {
                if (date.getHours() === now.getHours()) {
                  return minute < now.getMinutes();
                }
                return false;
              },
              isSecondDisabled: (second) => {
                if (date.getMinutes() === now.getMinutes()) {
                  return second < now.getSeconds();
                }
                return false;
              },
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
      this.formValue.value.description !== 'used for ci'
    ) {
      return h(
        'p',
        {
          style: {
            height: '20px',
          },
        },
        '请选择释放时间(默认1天)'
      );
    }
    return null;
  }
}

const handleSendRequest = (dOccupy, connect) => {
  dOccupy.content = '占用请求已发送';
  if (connect.formValue.value.description === 'used for ci') {
    return axios.put(`/v1/pmachine/${connect.formValue.value.id}/occupy`, {
      description: connect.formValue.value.description,
      occupier: storage.getValue('gitee_name'),
      user: connect.formValue.value.user,
    });
  } else if (connect.formValue.value.description !== 'as the host of ci') {
    return axios.put(`/v1/pmachine/${connect.formValue.value.id}/occupy`, {
      description: connect.formValue.value.description,
      end_time: any2standard(connect.datetime.value),
      occupier: storage.getValue('gitee_name'),
      user: connect.formValue.value.user,
    });
  }
  return axios.put(`/v1/pmachine/${connect.formValue.value.id}/occupy`, {
    description: connect.formValue.value.description,
    listen: connect.formValue.value.listen,
    occupier: storage.getValue('gitee_name'),
    user: connect.formValue.value.user,
  });
};

const handleOccupy = async (dOccupy, connect) => {
  return new Promise((resolve) => {
    new Promise((resolveWaitSend) => setTimeout(resolveWaitSend, 1000))
      .then(() => handleSendRequest(dOccupy, connect))
      .then((res) => {
        dOccupy.content = '物理机已成功占用';
        return Promise.resolve(res);
      })
      .catch((err) => {
        if (err.error_msg) {
          window.$message?.error(err.error_msg);
        } else if (err.message) {
          window.$message?.error(err.message);
        } else if (err.data.validation_error) {
          window.$message?.error(err.data.validation_error.body_params[0].msg);
        } else {
          window.$message?.error('发生未知错误，请联系管理员进行处理');
        }
        connect.clean();
      })
      .then(resolve);
  });
};

const handleRelease = (dRelease, connect) => {
  return new Promise((resolve, reject) => {
    dRelease.content = '释放请求已发送';
    axios
      .put(`/v1/pmachine/${connect.formValue.value.id}/release`)
      .then(() => {
        dRelease.content = '物理机已确认释放';
        resolve();
      })
      .catch((err) => {
        if (err.error_msg) {
          window.$message?.error(err.error_msg);
        } else if (err.message) {
          window.$message?.error(err.message);
        } else if (err.data.validation_error) {
          window.$message?.error(err.data.validation_error.body_params[0].msg);
        } else {
          window.$message?.error('发生未知错误，请联系管理员进行处理');
        }
        connect.clean();
        reject(err);
      });
  });
};

const handlePositiveClick = (dOccupy, connect) => {
  if (
    connect.formValue.value.description !== 'as the host of ci' 
    && connect.formValue.value.defaultValue !== 'used for ci'
    && !connect.datetime.value
  ) {
    window.$message?.error('此用途释放时间不可为空');
    return new Promise();
  }
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
      inputProps: {
        focus: false,
      },
      placeholder: '请输入使用说明',
    }),
    connect.listenText(),
    connect.listenElement(),
    connect.datePickerText(),
    connect.datePickerElement(),
  ]);
};

const handleConnectClick = (data, type) => {
  const connect = new ConnectState(data);
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

export { ConnectState, handleConnectClick };
