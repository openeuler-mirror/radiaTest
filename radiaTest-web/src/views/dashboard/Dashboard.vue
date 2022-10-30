<template>
  <div class="home">
    <transition name="mode-fade" mode="out-in">
      <div
        class="home-container"
        style="height: 100%"
        v-if="!showWorkbench"
        @wheel="handleWheelDown"
      >
        <div class="homeContent">
          <div style="margin-top: -30px">
            <div class="title">radiaTest</div>
            <div class="subtitle">版本级一站式测试平台</div>
            <n-space class="quickSpace">
              <home-button class="quickButton" @click="handleWorkbenchClick">
                工作台
              </home-button>
              <home-button
                class="quickButton"
                @click="handleGuideClick"
                invert-color
              >
                使用指南
              </home-button>
              <div class="gitee" @click="handleGiteeClick">
                <n-icon size="70" style="top: 3px">
                  <svg
                    width="1rem"
                    height="1rem"
                    xmlns="http://www.w3.org/2000/svg"
                    name="zi_tmGitee"
                    viewBox="0 0 2000 2000"
                  >
                    <path
                      d="M898 1992q183 0 344-69.5t283-191.5q122-122 191.5-283t69.5-344q0-183-69.5-344T1525 477q-122-122-283-191.5T898 216q-184 0-345 69.5T270 477Q148 599 78.5 760T9 1104q0 183 69.5 344T270 1731q122 122 283 191.5t345 69.5zm199-400H448q-17 0-30.5-14t-13.5-30V932q0-89 43.5-163.5T565 649q74-45 166-45h616q17 0 30.5 14t13.5 31v111q0 16-13.5 30t-30.5 14H731q-54 0-93.5 39.5T598 937v422q0 17 14 30.5t30 13.5h416q55 0 94.5-39.5t39.5-93.5v-22q0-17-14-30.5t-31-13.5H842q-17 0-30.5-14t-13.5-31v-111q0-16 13.5-30t30.5-14h505q17 0 30.5 14t13.5 30v250q0 121-86.5 207.5T1097 1592z"
                    />
                  </svg>
                </n-icon>
              </div>
            </n-space>
          </div>
        </div>
        <div class="img"></div>
      </div>
      <task-manage v-else />
    </transition>
  </div>
</template>

<script>
import { defineComponent } from 'vue';

import HomeButton from '@/components/public/HomeButton';
import taskManage from '@/views/taskManage/TaskManage';
import modules from './index';

export default defineComponent({
  components: {
    HomeButton,
    taskManage,
  },
  methods: {
    handleWorkbenchClick() {
      this.showWorkbench = true;
    },
  },
  setup() {
    modules.thirdPartLogin();
    modules.initData();
    return {
      ...modules,
      handleGuideClick() {
        window.open(
          'https://gitee.com/openeuler/radiaTest/blob/master/doc/radiaTest%E4%BD%BF%E7%94%A8%E6%8C%87%E5%8D%97.md'
        );
      }
    };
  },
});
</script>

<style scoped lang="less">
.home-container {
  display: flex;
  justify-content: space-around;
  width: 100%;
}
.title {
  font-size: 140px;
  font-family: v-sans;
  font-weight: 800;
}
.subtitle {
  font-size: 30px;
  color: grey;
  margin: 10px 0 40px 0;
}
.gitee {
  margin-left: 30px;
  color: #c72722;
  border-radius: 100%;
  border-style: solid;
  border-width: 0px;
  box-sizing: border-box;
  height: 82px;
  width: 82px;
  padding-left: 10px;
  transition: box-shadow 0.2s ease-in-out;
}
.gitee:hover {
  cursor: pointer;
  box-shadow: 8px 8px 20px rgb(152, 152, 152);
}
.homeContent {
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.img {
  width: 729px;
  background-image: url('@/assets/images/programming.png');
  background-repeat: no-repeat;
  background-size: contain;
  background-position: center;
}
@media screen and (max-width: 827px) {
  .quickSpace {
    display: block !important;
  }
}
@media screen and (max-width: 827px) {
  .quickButton {
    width: 40%;
    text-align: center;
  }
}
@media screen and (max-width: 827px) {
  .gitee {
    text-align: center;
    margin-left: 25% !important;
  }
}
@media screen and (max-width: 525px) {
  .title {
    display: none;
  }
}
@media screen and (max-width: 525px) {
  .homeContent {
    top: -120% !important;
  }
}
@media screen and (max-width: 525px) {
  .subtitle {
    color: black !important;
  }
}
@media screen and (max-width: 525px) {
  .img {
    left: 0% !important;
    opacity: 0.5;
  }
}
</style>
