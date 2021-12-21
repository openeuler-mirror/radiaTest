<template>
  <div class="login-page">
    <div
      class="left-slider"
      :style="{ borderWidth: `${windowHeight}px 0 0 ${windowWidth * 0.4}px` }"
    ></div>
    <div
      class="bottom-slider"
      :style="{
        borderWidth: `${windowHeight * 0.8}px 0 0 ${windowWidth * 0.6}px`,
      }"
    ></div>
    <div class="carousel-container">
      <carousel
        :sliders="sliders"
        :duration="6000"
        :autoplay="true"
        @change="indexChange"
        :mouseStop="true"
      >
        <template v-slot:imgTop-0>
          <div :class="{ loginActive: activeIndex === 0 || activeIndex === 5 }">
            <p class="carousel-description">
              便捷轻松地管理测试任务，
            </p>
            <p class="carousel-description">
              为团队效率加速
            </p>
          </div>
        </template>
        <template v-slot:imgTop-1>
          <div :class="{ loginActive: activeIndex === 1 }">
            <p class="carousel-description">
              文本用例集中管理，
            </p>
            <p class="carousel-description">
              更有线上评审功能
            </p>
          </div>
        </template>
        <template v-slot:imgTop-2>
          <div :class="{ loginActive: activeIndex === 2 }">
            <p class="carousel-description">
              测试环境一键部署，
            </p>
            <p class="carousel-description">
              测试用例自动执行
            </p>
          </div>
        </template>
        <template v-slot:imgTop-3>
          <div :class="{ loginActive: activeIndex === 3 }">
            <p class="carousel-description">
              测试报告一键生成，
            </p>
            <p class="carousel-description">
              全面助力版本级测试
            </p>
          </div>
        </template>
        <template v-slot:imgTop-4>
          <div :class="{ loginActive: activeIndex === 4 }">
            <p class="carousel-description">
              资源池分布式管理，
            </p>
            <p class="carousel-description">
              实现高效智能化调度
            </p>
          </div>
        </template>
      </carousel>
    </div>
    <n-card class="login-box" :bordered="false" :segmented="{ footer: 'hard' }">
      <div style="text-align:center">
        <span id="radiaTest">
          <n-gradient-text type="primary">radiaTest</n-gradient-text>
        </span>
      </div>
      <n-tabs
        default-value="signin"
        size="large"
        justify-content="space-around"
      >
        <n-tab-pane name="signin" tab="用户登录">
          <n-form>
            <n-form-item style="--label-height:6px">
              <n-input
                round
                size="large"
                placeholder="请输入用户名"
                type="text"
                :disabled="true"
              >
                <template #prefix>
                  <n-icon size="20">
                    <user />
                  </n-icon>
                </template>
              </n-input>
            </n-form-item>
            <n-form-item style="--label-height:6px">
              <n-input
                round
                size="large"
                placeholder="请输入密码"
                type="password"
                :disabled="true"
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
            type="error"
            block
            round
            style="margin-top:10px"
            @click="hanleLogin"
          >
            <span class="iconfont icon-gitee2"></span>
            <span style="margin-left:10px">码云鉴权登录</span>
          </n-button>
        </n-tab-pane>
        <n-tab-pane name="signup" tab="管理员登录" v-if="!isFrame">
          <div id="loginForm">
            <n-form :rules="rules" :model="loginForm" ref="loginFormRef">
              <n-form-item style="--label-height:6px" path="userName">
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
              <n-form-item style="--label-height:6px" path="passWord">
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
              >登录</n-button
            >
          </div>
        </n-tab-pane>
      </n-tabs>
      <template #footer>
        <p style="text-align:center">
          {{ `${config.name} ${config.version}·${config.license}` }}
        </p>
      </template>
    </n-card>
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
        <n-steps size="small" :current="current" :status="currentStatus">
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
              <n-select v-model:value="loginInfo.org" :options="orgList" />
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
            <n-result status="success" title="注册成功">
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
              <n-select v-model:value="loginInfo.org" :options="orgList" />
            </div>
            <div style="text-align:center;">
              <n-tooltip placement="bottom" trigger="hover">
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
          size="large"
          v-show="contentName === 'perfectInfo' && stepList.length === 4"
          >上一步</n-button
        >
        <n-button
          @click="nextStep"
          type="primary"
          size="large"
          ghost
          v-show="current !== stepList.length"
          >下一步</n-button
        >
      </template>
    </n-modal>
  </div>
</template>
<script>
import config from '@/assets/config/settings';
import { ref } from 'vue';
import { modules } from './modules/index';
import { useMessage } from 'naive-ui';
import { User, Lock } from '@vicons/fa';
import carousel from '@/components/carousel/carousel.vue';
export default {
  components: {
    User,
    Lock,
    carousel,
  },
  methods: {
    indexChange(index) {
      this.activeIndex = index;
    },
  },
  setup() {
    const message = useMessage();
    window.$message = message;
    modules.gotoHome();
    modules.isIframe();
    const windowHeight = window.innerHeight;
    const windowWidth = window.innerWidth;
    const activeIndex = ref(0);
    const sliders = [
      { id: 1, imgUrl: '/nextTasks.png' },
      { id: 2, imgUrl: '/annotation.png' },
      { id: 3, imgUrl: '/programming.png' },
      { id: 4, imgUrl: '/report.png' },
      { id: 5, imgUrl: '/server.png' },
    ];
    return {
      sliders,
      windowHeight,
      windowWidth,
      config,
      activeIndex,
      ...modules,
    };
  },
};
</script>
<style lang="less">
.carousel-description {
  margin: 0;
  padding: 0;
}
@font-face {
  font-family: 'iconfont'; /* Project id  */
  src: url('iconfont.ttf?t=1638788508582') format('truetype');
}

.iconfont {
  font-family: 'iconfont' !important;
  font-size: 24px;
  font-style: normal;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.icon-gitee2:before {
  content: '\e677';
}

.loginActive {
  animation: fadeInUp;
  animation-duration: 2s;
}
.carousel-description {
  height: 35px;
  font-size: 30px;
  line-height: 35px;
  text-align: right;
  color: #204295;
}

.login-page {
  height: 100%;
  position: relative;
  .login-box {
    z-index: 99;
    width: 400px;
    position: fixed;
    right: 10%;
    padding-top: 10%;
    #radiaTest {
      font-size: 52px;
      font-family: 'v-sans';
      width: 100%;
      .n-gradient-text {
        font-weight: 800;
      }
    }
  }
  .carousel-container {
    position: fixed;
    bottom: 300px;
    left: 10%;
    width: 800px;
    height: 480px;
    background-color: #fff;
    z-index: 98;
    .carousel {
      height: 608px;
      .carousel-item {
        .carousel-img {
          object-fit: fill;
          height: 480px;
          width: 608px;
        }
      }
    }
  }
  .left-slider {
    position: fixed;
    left: 0;
    border-style: solid;
    border-color: rgba(0, 47, 167, 1) transparent transparent transparent;
    width: 0;
    height: 0;
    transform: rotate(180deg);
    z-index: 999;
  }
  .bottom-slider {
    position: fixed;
    bottom: 0;
    border-style: solid;
    border-color: rgba(0, 47, 167, 0.5) transparent transparent transparent;
    width: 0;
    height: 0;
    transform: rotate(180deg);
  }
}
</style>
