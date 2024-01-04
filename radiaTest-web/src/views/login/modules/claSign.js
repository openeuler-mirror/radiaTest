import { reactive, ref } from 'vue';

import { orgList } from './org';
import axios from '@/axios';
import router from '@/router/index';
import { openChildWindow, urlArgs } from '@/assets/utils/urlUtils';
import { addRoom } from '@/assets/utils/socketUtils';
import { storage } from '@/assets/utils/storageUtils';
import { registerShow, requireCLA } from './login';
import CryptoJS from 'crypto-js';

const route = urlArgs();

const loginInfo = reactive({ org: '', claEmail: '' });
const claEmailRule = {
  trigger: ['blur'],
  required: true,
  validator() {
    if (loginInfo.claEmail) {
      const emailReg =
        /^[a-zA-Z0-9\u4e00-\u9fa5_.-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z0-9]{2,6}$/;
      if (!emailReg.test(loginInfo.claEmail)) {
        return new Error('邮箱格式不对!');
      }
      return true;
    }
    return new Error('cla邮箱不能为空!');
  },
};
const orgNameRule = {
  trigger: ['blur', 'change'],
  required: true,
  message: '组织不能为空',
  validator() {
    if (loginInfo.org) {
      return true;
    }
    return false;
  },
};
const stepList = ref([
  { title: 'Gitee授权', status: 'finish' },
  {
    title: '信息完善',
    name: 'perfectInfo',
    status: 'wait',
  },
  { title: '注册成功', name: 'success', status: 'wait' },
]);
const current = ref(2);
const contentName = ref(stepList.value[current.value - 1].name);
function gotoCLA() {
  const itemCla = orgList.value.find((item) => {
    return item.value === loginInfo.org;
  });
  openChildWindow(itemCla.jumpUrl);
}
function perfectInfo() {
  const userId = route.user_id;
  if (
    (!requireCLA.value ||
      (claEmailRule.validator() && typeof claEmailRule.validator() !== 'object')) &&
    orgNameRule.validator()
  ) {
    let timestamp = Date.now();
    const token =
      'eyJhbGciOiJIUzUxMiIsImlhdCI6MTcwNDM0ODkxMywiZXhwIjoxNzA0Mzc3NzEzfQ.ip54BRH2LvXcYtpr0BABpSamMPlD+QaWHwsBLL14BlxKTP5EkXbI2cdEeElh1fwXoHSF0PzXE+/E/KikO5EUvCEP+cE8pOMO2dlzNvgnTY0=.4VOSqS8iIigrPFhC7uV3WBrgmxl5dmYOX803lUzWaT_SCPHpBWtFGdEO5gd_Z97GuKVDkyK3YRmY-3XfREXRlw';
    const secretKey = '87f364ec2db54a2ca23681542e4d5a87';
    let message = token + timestamp;
    const hash = CryptoJS.HmacSHA256(message, secretKey);
    const hashInHex = CryptoJS.enc.Base64.stringify(hash);
    axios
      .post(
        `/v1/users/${userId}`,
        {
          cla_verify_params: requireCLA.value ? JSON.stringify({ email: loginInfo.claEmail }) : '',
          organization_id: loginInfo.org,
        },
        {
          headers: {
            timestamp,
            sign: hashInHex,
          },
        }
      )
      .then((res) => {
        storage.setValue('token', res.data.token);
        storage.setValue('user_id', userId);
        stepList.value[current.value - 1].status = 'finish';
        current.value++;
        contentName.value = stepList.value[current.value - 1].name;
        setTimeout(() => {
          registerShow.value = false;
          router.push({ name: 'home' }).then(() => {
            addRoom(storage.getValue('token'));
          });
        }, 1000);
      })
      .catch((err) => {
        if (err.data.error_code === '4010') {
          window.$message.warning('请先签署CLA');
          stepList.value = [
            { title: 'Gitee授权', status: 'finish' },
            {
              title: 'CLA签署',
              name: 'signCLA',
              status: 'wait',
            },
            {
              title: '信息完善',
              name: 'perfectInfo',
              status: 'wait',
            },
            { title: '注册成功', name: 'success', status: 'wait' },
          ];
          current.value = 2;
          contentName.value = 'signCLA';
        } else {
          window.$message?.error(err.data.error_msg || '未知错误');
        }
      });
  } else {
    window.$message.error('请填写相关信息');
  }
}
function nextStep() {
  if (stepList.value[current.value - 1].name === 'perfectInfo') {
    perfectInfo();
  }
  if (stepList.value[current.value - 1].name === 'signCLA') {
    current.value++;
    contentName.value = stepList.value[current.value - 1].name;
    stepList.value[1].status = 'process';
  }
}
function prevStep() {
  current.value--;
  stepList.value[current.value - 1].status = 'wait';
  contentName.value = stepList.value[current.value - 1].name;
}

export {
  loginInfo,
  claEmailRule,
  orgNameRule,
  stepList,
  contentName,
  current,
  gotoCLA,
  prevStep,
  nextStep,
};
