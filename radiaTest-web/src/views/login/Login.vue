<template>
  <n-spin
    :show="showLoading"
    stroke="rgba(0, 47, 167, 1)"
  >
    <div
      id="login-page"
      :style="{ height: windowHeight + 'px' }"
    >
      <n-carousel
        autoplay
        trigger="click"
        class="carousel"
      >
        <img
          style="height:100%"
          v-for="(item,index) in carouselImgs"
          :key="index"
          class="carousel-img"
          :src="item.src"
        />
      </n-carousel>
      <div id="login-box">
        <div id="box-header">
          <div><span id="m">M</span><span id="ugen">ugen</span></div>
        </div>
        <n-tabs
          default-value="signin"
          size="large"
          justify-content="center"
          style="margin-top:100px"
        >
          <n-tab-pane
            name="signin"
            tab="gitee登录"
          >
            <div style="display:flex;justify-content:center">
              <div
                id="login"
                @click="hanleLogin"
              ></div>
            </div>
          </n-tab-pane>
          <n-tab-pane
            name="signup"
            tab="管理员登录"
            v-if="!isFrame"
          >
            <div id="loginForm">
              <n-form
                :rules="rules"
                :model="loginForm"
                ref="loginFormRef"
              >
                <n-form-item
                  style="--label-height:6px"
                  path="userName"
                >
                  <n-input
                    round
                    size="large"
                    placeholder="请输入用户名"
                    v-model:value="loginForm.userName"
                    type="text"
                  >
                    <template #prefix>
                      <n-icon size="20">
                        <user />
                      </n-icon>
                    </template>
                  </n-input>
                </n-form-item>
                <n-form-item
                  style="--label-height:6px"
                  path="passWord"
                >
                  <n-input
                    round
                    size="large"
                    placeholder="请输入密码"
                    type="password"
                    v-model:value="loginForm.passWord"
                  >
                    <template #prefix>
                      <n-icon size="20">
                        <lock />
                      </n-icon>
                    </template>
                  </n-input>
                </n-form-item>
              </n-form>
              <n-button
                type="primary"
                block
                round
                style="margin-top:10px"
                @click="handleLoginByForm"
              >登录</n-button>
            </div>
          </n-tab-pane>
        </n-tabs>
      </div>
      <n-modal
        v-model:show="registerShow"
        preset="dialog"
        :show-icon="false"
        :mask-closable="false"
        title="Dialog"
        :closable="regCancel"
        :style="{ width: stepList.length * 150 + 200 + 'px' }"
      >
        <template #header>
          <h3>用户注册</h3>
        </template>
        <div>
          <n-steps
            size="small"
            :current="current"
            :status="currentStatus"
          >
            <n-step
              :title="item.title"
              v-for="(item, index) in stepList"
              :key="index"
              :status="item.status"
            >
            </n-step>
          </n-steps>
          <div class="registerContent">
            <div v-if="contentName === 'perfectInfo'">
              <n-form-item
                label="组织"
                :rule="orgNameRule"
                label-placement="left"
                label-align="left"
                label-width="100"
              >
                <n-select
                  v-model:value="loginInfo.org"
                  :options="orgList"
                />
              </n-form-item>
              <n-form-item
                label="cla邮箱"
                :rule="claEmailRule"
                label-placement="left"
                label-align="left"
                label-width="100"
              >
                <n-input
                  v-model:value="loginInfo.claEmail"
                  style="margin:5px 0"
                />
              </n-form-item>
            </div>
            <div v-if="contentName === 'success'">
              <n-result
                status="success"
                title="注册成功"
              >
                <template #footer>
                  即将为您跳转主页...
                </template>
              </n-result>
            </div>
            <div
              v-if="contentName === 'signCLA'"
              style="height:100%;display: flex;flex-direction: column;justify-content: space-around;"
            >
              <div style="display:flex;align-items:center;">
                <p style="width:50px;flex-shrink:0">组织:</p>
                <n-select
                  v-model:value="loginInfo.org"
                  :options="orgList"
                />
              </div>
              <div style="text-align:center;">
                <n-tooltip
                  placement="bottom"
                  trigger="hover"
                >
                  <template #trigger>
                    <img
                      style="width:100px;cursor:pointer;"
                      :src="claImgUrl"
                      @click="gotoCLA"
                    />
                  </template>
                  点击前往CLA签署界面
                </n-tooltip>
                <p style="margin:5px 0">点击图片前往CLA签署界面</p>
              </div>
            </div>
          </div>
        </div>
        <template #action>
          <n-button
            @click="prevStep"
            type="primary"
            ghost
            v-show="contentName === 'perfectInfo' && stepList.length === 4"
          >上一步</n-button>
          <n-button
            @click="nextStep"
            type="primary"
            ghost
            v-show="current !== stepList.length"
          >下一步</n-button>
        </template>
      </n-modal>
    </div>
  </n-spin>
</template>
<script>
import { defineComponent, ref } from 'vue';
import { useMessage } from 'naive-ui';
import claImgUrl from '@/assets/images/cla.jpg';
import { User, Lock } from '@vicons/fa';
import axios from 'axios';

import { modules } from './modules/index';

export default defineComponent({
  components: {
    User,
    Lock,
  },
  setup () {
    const windowHeight = document.body.clientHeight;
    const carouselImgs = ref([]);
    const imgUrl = ['/version.jpg', '/source.jpg', '/implement.jpg', '/task.jpg', '/example.jpg'];
    for (let i = 0; i < imgUrl.length; i++) {
      carouselImgs.value.push({
        src: ''
      });
    }
    const message = useMessage();
    window.$message = message;
    modules.gotoHome();
    modules.isIframe();
    Promise.allSettled(imgUrl.map(item => axios.get(item, { responseType: 'arraybuffer' }))).then(responses => {
      for (let i = 0; i < responses.length; i++) {
        const item = responses[i];
        if (item.status === 'fulfilled') {
          carouselImgs.value[i].src = `data:image/png;base64, ${btoa(
            new Uint8Array(item.value.data).reduce((data, byte) => data + String.fromCharCode(byte), '')
          )}`;
        }
      }
    }).catch(() => {
      window.$message?.error('图片加载失败!');
    });
    return { windowHeight, claImgUrl, carouselImgs, ...modules };
  },
});
</script>
<style lang="less">
.registerContent {
  height: 200px;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 5px;
  > div {
    width: 100%;
  }
}
.carousel-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
#login-page {
  background-color: #a9b3da;
  display: flex;
  .carousel {
    width: 100%;
  }
  .n-tabs-tab-wrapper {
    margin: 0 10px;
  }

  #login-box {
    height: 100%;
    width: 400px;
    flex-shrink: 0;
    background-color: rgba(255, 255, 255, 0.5);
    background-image: url("../../assets/images/intro.png");
    background-repeat: no-repeat;
    background-position: bottom;

    #box-header {
      height: 100px;
      margin-top: 100px;
      display: flex;
      justify-content: center;
      align-items: center;

      #m {
        font-size: 64px;
        font-family: "v-sans";
        font-weight: 800;
        width: 100%;
        color: rgba(0, 47, 167, 1);
        text-shadow: 1px 1px 4px rgba(0, 47, 167, 1);
      }

      #ugen {
        font-size: 50px;
        font-family: "v-mono";
        font-weight: 400;
        width: 100%;
        color: rgba(0, 47, 167, 1);
        text-shadow: 3px 3px 8px rgba(0, 47, 167, 1);
      }
    }

    .tip-title {
      margin-top: 10px;
      height: 50px;
      line-height: 50px;
      text-align: center;
      font-weight: bold;
      font-size: 18px;
      color: rgba(0, 47, 167, 1);
    }

    #login {
      background-image: url("../../assets/images/gitee.png");
      height: 150px;
      width: 150px;
      margin-top: 16px;
      cursor: pointer;
      background-position: center;
    }

    #loginForm {
      width: 90%;
      position: relative;
      left: 50%;
      transform: translateX(-50%);
    }
  }
}
</style>
