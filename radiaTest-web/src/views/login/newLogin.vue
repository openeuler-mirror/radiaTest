<template>
  <div class="login-page" v-if="hasSigned === true">
    <n-result status="info" title="登录" description="正在奋力登录中......"> </n-result>
  </div>
  <div class="privacy-agreement" v-else>
    <n-card embedded :bordered="false" class="agreement">
      <div>
        <h3 style="text-align: center">《用户隐私协议》</h3>
        <p>
          海伦融媒客户端是由黑龙江广播电视网络股份有限公司提供。您在使用“海伦融媒”客户端时，我们可能会收集和使用您的相关信息。我们深知个人信息对您的重要性，因此我们非常重视保护您的隐私和个人信息，我们会将本隐私协议中的内容以高度审慎的义务对待和处理，并将恪守以下原则，保护您的个人信息：权责一致原则、目的明确原则、选择同意原则、最少够用原则、公开透明原则、确保安全原则、主体参与原则、公开透明原则等。我们将按照法律法规的规定并参照行业最佳实践保护您的个人信息及隐私安全。
          您在下载、安装、启动、浏览、注册、登录、使用海伦融媒时，我们将按照本政策的约定处理和保护您的个人信息，因此我们希望您能够仔细阅读、充分理解本政策的全文，并在需要时，按照本政策的指引，作出您认为适当的选择。
          我们会遵循隐私政策收集、使用您的信息，但不会仅因您同意本隐私政策而采用强制捆绑的方式一揽子收集个人信息。当您使用或开启相关功能或使用服务时，为实现功能、服务所必需，我们会收集、使用相关信息。除非是为实现基本业务功能或根据法律法规要求所必需的必要信息，您均可以拒绝提供且不影响其他功能或服务。我们将在隐私政策中逐项说明哪些是必要信息。
        </p>
        <p>
          如果您未登录帐号，我们会通过设备对应的标识符信息来保障信息推送的基本功能。如果您登录了帐号，我们会根据帐号信息实现信息推送。
          精确地理位置、摄像头、麦克风、相册（存储），均不会默认开启，只有经过您的明示授权才会在为实现特定功能或服务时使用，您也可以撤回授权。特别需要指出的是，即使经过您的授权，我们获得了这些敏感权限，也不会在相关功能或服务不需要时而收集您的信息。
          请您注意，本隐私政策不适用于其他第三方向您提供的服务（包括任何第三方应用、网站、产品、服务等，如第三方支付渠道），您向第三方提供的个人信息不适用于本隐私政策，除非法律有明确规定，我们对任何第三方收集、储存和使用的您个人信息的行为不承担任何责任。
        </p>
        <p>
          如果您未登录帐号，我们会通过设备对应的标识符信息来保障信息推送的基本功能。如果您登录了帐号，我们会根据帐号信息实现信息推送。
          精确地理位置、摄像头、麦克风、相册（存储），均不会默认开启，只有经过您的明示授权才会在为实现特定功能或服务时使用，您也可以撤回授权。特别需要指出的是，即使经过您的授权，我们获得了这些敏感权限，也不会在相关功能或服务不需要时而收集您的信息。
          请您注意，本隐私政策不适用于其他第三方向您提供的服务（包括任何第三方应用、网站、产品、服务等，如第三方支付渠道），您向第三方提供的个人信息不适用于本隐私政策，除非法律有明确规定，我们对任何第三方收集、储存和使用的您个人信息的行为不承担任何责任。
        </p>
        <p>
          如果您未登录帐号，我们会通过设备对应的标识符信息来保障信息推送的基本功能。如果您登录了帐号，我们会根据帐号信息实现信息推送。
          精确地理位置、摄像头、麦克风、相册（存储），均不会默认开启，只有经过您的明示授权才会在为实现特定功能或服务时使用，您也可以撤回授权。特别需要指出的是，即使经过您的授权，我们获得了这些敏感权限，也不会在相关功能或服务不需要时而收集您的信息。
          请您注意，本隐私政策不适用于其他第三方向您提供的服务（包括任何第三方应用、网站、产品、服务等，如第三方支付渠道），您向第三方提供的个人信息不适用于本隐私政策，除非法律有明确规定，我们对任何第三方收集、储存和使用的您个人信息的行为不承担任何责任。
        </p>
        <p>
          如果您未登录帐号，我们会通过设备对应的标识符信息来保障信息推送的基本功能。如果您登录了帐号，我们会根据帐号信息实现信息推送。
          精确地理位置、摄像头、麦克风、相册（存储），均不会默认开启，只有经过您的明示授权才会在为实现特定功能或服务时使用，您也可以撤回授权。特别需要指出的是，即使经过您的授权，我们获得了这些敏感权限，也不会在相关功能或服务不需要时而收集您的信息。
          请您注意，本隐私政策不适用于其他第三方向您提供的服务（包括任何第三方应用、网站、产品、服务等，如第三方支付渠道），您向第三方提供的个人信息不适用于本隐私政策，除非法律有明确规定，我们对任何第三方收集、储存和使用的您个人信息的行为不承担任何责任。
        </p>
        <p>
          如果您未登录帐号，我们会通过设备对应的标识符信息来保障信息推送的基本功能。如果您登录了帐号，我们会根据帐号信息实现信息推送。
          精确地理位置、摄像头、麦克风、相册（存储），均不会默认开启，只有经过您的明示授权才会在为实现特定功能或服务时使用，您也可以撤回授权。特别需要指出的是，即使经过您的授权，我们获得了这些敏感权限，也不会在相关功能或服务不需要时而收集您的信息。
          请您注意，本隐私政策不适用于其他第三方向您提供的服务（包括任何第三方应用、网站、产品、服务等，如第三方支付渠道），您向第三方提供的个人信息不适用于本隐私政策，除非法律有明确规定，我们对任何第三方收集、储存和使用的您个人信息的行为不承担任何责任。
        </p>
        <p>
          如果您未登录帐号，我们会通过设备对应的标识符信息来保障信息推送的基本功能。如果您登录了帐号，我们会根据帐号信息实现信息推送。
          精确地理位置、摄像头、麦克风、相册（存储），均不会默认开启，只有经过您的明示授权才会在为实现特定功能或服务时使用，您也可以撤回授权。特别需要指出的是，即使经过您的授权，我们获得了这些敏感权限，也不会在相关功能或服务不需要时而收集您的信息。
          请您注意，本隐私政策不适用于其他第三方向您提供的服务（包括任何第三方应用、网站、产品、服务等，如第三方支付渠道），您向第三方提供的个人信息不适用于本隐私政策，除非法律有明确规定，我们对任何第三方收集、储存和使用的您个人信息的行为不承担任何责任。
        </p>
        <p>
          如果您未登录帐号，我们会通过设备对应的标识符信息来保障信息推送的基本功能。如果您登录了帐号，我们会根据帐号信息实现信息推送。
          精确地理位置、摄像头、麦克风、相册（存储），均不会默认开启，只有经过您的明示授权才会在为实现特定功能或服务时使用，您也可以撤回授权。特别需要指出的是，即使经过您的授权，我们获得了这些敏感权限，也不会在相关功能或服务不需要时而收集您的信息。
          请您注意，本隐私政策不适用于其他第三方向您提供的服务（包括任何第三方应用、网站、产品、服务等，如第三方支付渠道），您向第三方提供的个人信息不适用于本隐私政策，除非法律有明确规定，我们对任何第三方收集、储存和使用的您个人信息的行为不承担任何责任。
        </p>
        <div class="agreement-radio">
          <n-space>
            <n-radio
              :checked="checkedValue === 'disagree'"
              value="disagree"
              name="basic-demo"
              size="large"
              @change="handleChange"
            >
              不同意
            </n-radio>
            <n-radio
              :checked="checkedValue === 'agree'"
              value="agree"
              name="basic-demo"
              size="large"
              @change="handleChange"
            >
              同意
            </n-radio>
          </n-space>
        </div>
      </div>
    </n-card>
  </div>
</template>
<script setup>
import { useDialog } from 'naive-ui';
import router from '@/router/index';
import { storage } from '@/assets/utils/storageUtils';
import { addRoom } from '@/assets/utils/socketUtils';
import { urlArgs, resUrlArgs } from '@/assets/utils/urlUtils';
import { loginByCode } from '@/api/get';
import { signPrivacy } from '@/api/post';
import axios from '@/axios';
const hasSigned = ref(true);
const resUrlSucess = ref(false);
const handleIsSuccess = () => {
  if (hasSigned.value) {
    if (urlArgs().isSuccess === 'True') {
      setTimeout(() => {
        router.push({ name: 'task' }).then(() => {
          addRoom(storage.getValue('token'));
        });
      }, 1000);
    } else if (urlArgs().isSuccess === 'False') {
      exitLogin();
    }
  } else if (!hasSigned.value) {
    if (resUrlArgs(resUrl.value).isSuccess === 'True') {
      resUrlSucess.value = true;
    } else if (urlArgs().isSuccess === 'False') {
      exitLogin();
    }
  }
};
const resUrl = ref(null);
// 进入登录页面
const gotoHome = () => {
  if (urlArgs().code) {
    loginByCode({
      code: urlArgs().code,
      org_id: storage.getValue('loginOrgId'),
      privacy_version: 'v1.0',
    })
      .then((res) => {
        hasSigned.value = res.data?.is_privacy_sign;
        storage.setValue('token', res.data?.token);
        storage.setValue('user_id', res.data?.user_id);
        storage.setLocalValue('unLoginOrgId', {
          name: res.data?.current_org_name,
          id: res.data?.current_org_id,
        });
        if (res.data?.is_privacy_sign) {
          window.location = res.data?.url; // login?isSuccess=True
        } else {
          resUrl.value = res.data?.url;
          handleIsSuccess();
        }
      })
      .catch((err) => {
        window.$message?.error(err?.data?.error_msg || '登录失败！');
        exitLogin();
      });
  }
  handleIsSuccess();
};

const dialog = useDialog();
const checkedValue = ref(null);
const handleChange = (e) => {
  if (e.target.value === 'agree') {
    dialog.warning({
      title: '警告',
      content: '你确定同意用户隐私协议吗？点击确定将签署协议直接登录',
      positiveText: '确定',
      negativeText: '不确定',
      onPositiveClick: () => {
        checkedValue.value = e.target.value;
        signPrivacy({ privacy_version: 'v1.0', is_sign: true })
          .then(() => {
            if (resUrlSucess) {
              router.push({ name: 'task' }).then(() => {
                addRoom(storage.getValue('token'));
              });
            }
          })
          .catch((err) => {
            window.$message?.error(err?.data?.error_msg || '签署隐私协议失败！');
          });
      },
      onNegativeClick: () => {
        checkedValue.value = null;
      },
    });
  } else if (e.target.value === 'disagree') {
    dialog.warning({
      title: '警告',
      content: '你确定不同意用户隐私协议吗？点击确定将退出登录',
      positiveText: '确定',
      negativeText: '不确定',
      onPositiveClick: () => {
        checkedValue.value = e.target.value;
        // 退出登录
        exitLogin();
      },
      onNegativeClick: () => {
        checkedValue.value = null;
      },
    });
  }
};
const exitLogin = () => {
  axios
    .delete('/v1/logout')
    .then((res) => {
      window.sessionStorage.clear();
      if (res.error_msg) {
        window.location = res.error_msg;
      } else {
        router.replace({
          name: 'task',
        });
      }
    })
    .catch((err) => {
      window.$message?.error(err?.data?.error_msg || '退出登录失败！');
    });
};
onMounted(() => {
  gotoHome();
});
</script>
<style lang="less">
.login-page {
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}
.privacy-agreement {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  .agreement {
    width: 60%;
    height: 100%;
    overflow-y: scroll;
    color: #3d526f;
    p {
      margin: 10px 0;
      text-indent: 30px;
      font-size: 16px;
    }
  }
  .agreement-radio {
    display: flex;
    justify-content: center;
    margin: 25px 0;
  }
}
</style>
