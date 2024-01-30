<script setup>
import { computed, onMounted } from 'vue';
import Vue3DraggableResizable from 'vue3-draggable-resizable';
import 'vue3-draggable-resizable/dist/Vue3DraggableResizable.css';
import { UpToTop, Close, DownToBottom } from '@vicons/carbon';
import { useMessage } from 'naive-ui';
import axios from '@/axios';

// pop1 start
const score = ref(0);

const isShow = ref(true);
const isReasonShow = ref(false);
const isDynamic = ref(false);
const inputText = ref('');
let timer;
const toggleIsShow = (toggle) => {
  if (!toggle && isReasonShow.value) {
    return;
  }
  if (timer) {
    clearTimeout(timer);
  }
  if (toggle) {
    isShow.value = toggle;
  } else {
    timer = setTimeout(() => {
      isShow.value = toggle;
    }, 2000);
  }
  setTimeout(() => {
    isDynamic.value = toggle;
  });
};
const closefloat = () => {
  score.value = 0;
  isDynamic.value = false;
};
function cancelPopup() {
  isReasonShow.value = false;
  inputText.value = '';
  score.value = 0;
  isDynamic.value = false;
  timer = setTimeout(() => {
    isShow.value = false;
  }, 2000);
}

function handleInput(value) {
  score.value = value;
  isReasonShow.value = true;
}

const STEP = 10;

const marks = computed(() => {
  let temp = {};
  for (let i = 0; i < STEP + 1; i++) {
    temp[i] = '';
  }
  return temp;
});

const infoData = {
  grade1_1: '0-不满意',
  grade2_1: '10-非常满意',
  placeholder1: '请输入您不太满意的原因（0-6）',
  placeholder2: '改进哪些方面会让您更满意？（7-8）',
  placeholder3: '请输入您满意的原因（9-10）',
  more1: '感谢您的反馈，如需帮助，可论坛',
  more2: '发帖求助',
  more2Link: 'https://forum.openeuler.org/',
  submit: '提交',
  cancel: '取消',
  confirm: '确认',
  feedbackTitle: '满意度反馈',
  welcome: '欢迎在此反馈您在社区体验中的任何建议或问题',
  know: '知道了',
};
const placeholder = computed(() => {
  let reasons;
  if (score.value < 7) {
    reasons = '请输入您不太满意的原因';
  } else if (score.value < 9) {
    reasons = '改进哪些方面会让您更满意？';
  } else {
    reasons = '请输入您满意的原因';
  }
  return reasons;
});
const isFocuse = ref(false);
const textareaRef = ref(null);
onMounted(() => {
  if (textareaRef.value) {
    textareaRef.value.addEventListener('focus', () => {
      isFocuse.value = true;
    });
    textareaRef.value.addEventListener('blur', () => {
      isFocuse.value = false;
    });
  }
});

const floatData = ref([
  {
    text: '欧拉小智',
    tip: '提供自助问答与咨询',
    id: 'robot',
    link: 'https://qa-robot.openeuler.org/',
  },
  {
    text: '欧拉论坛',
    tip: '发帖互助解决各类问题',
    id: 'forum',
    link: 'https://forum.openeuler.org/',
  },
  {
    id: 'quickIssue',
    text: 'QuickIssue',
    tip: '快捷提交/查询社区Issues',
    link: 'https://quickissue.openeuler.org/zh/issues/',
  },
]);
const route = useRoute();
function handleClickTop() {
  if (route.name === 'resourcePool') {
    document.querySelector('#resourcePoolRight > div').scrollTop = 0;
  } else if (route.name === 'folderview') {
    document.querySelector('#folderviewRight > div').scrollTop = 0;
  } else {
    document.querySelector('#homeBody > div').scrollTop = 0;
  }
}
const backToBottom = () => {
  if (route.name === 'resourcePool') {
    document.querySelector('#resourcePoolRight > div').scrollTop = document.querySelector(
      '#resourcePoolRight > div'
    ).scrollHeight;
  } else if (route.name === 'folderview') {
    document.querySelector('#folderviewRight > div').scrollTop =
      document.querySelector('#folderviewRight > div').scrollHeight;
  } else {
    document.querySelector('#homeBody > div').scrollTop =
      document.querySelector('#homeBody > div').scrollHeight;
  }
};
function postScore() {
  if (!isReasonShow.value) {
    return;
  }
  const params = {
    // userName: guardAuthClient.value.username,
    feedbackPageUrl: window.location.href,
    feedbackText: inputText.value,
    feedbackValue: score.value,
  };
  axios
    .post('https://www.openeuler.org/api-dsapi/query/nps?community=openeuler', params)
    .then((res) => {
      if (res.code === 200) {
        window.$message?.success('提交成功，感谢您的反馈！');
        const summitTime = new Date().valueOf();
        localStorage.setItem('submit-time', JSON.stringify(summitTime));
        isReasonShow.value = false;
        inputText.value = '';
        score.value = 0;
        isDynamic.value = false;
      } else {
        console.log('else', res);
        window.$message?.error(res.msg || '未知错误');
      }
    })
    .catch((err) => {
      console.log('err', err);
      window.$message?.error(err || '未知错误');
    });
}
const message = useMessage();
function handleClickSubmit() {
  // pc12小时之内只能提交一次
  const lastSummitTIME = localStorage.getItem('submit-time');
  const intervalTime = 1 * 12 * 60 * 60 * 1000;
  const nowTime = new Date().valueOf();
  if (lastSummitTIME) {
    const flag = nowTime - JSON.parse(lastSummitTIME) > intervalTime;
    if (flag) {
      postScore();
    } else {
      console.log('请不要频繁提交！');
      message.warning('请不要频繁提交！');
    }
  } else {
    postScore();
  }
}

const jumpToGitee = () => {
  window.open('https://gitee.com/openeuler/radiaTest');
};
</script>

<template>
  <div class="float">
    <vue3-draggable-resizable
      :draggable="true"
      :resizable="false"
      classNameDraggable="dragwrapbox"
      :h="dragboxHeight"
      :initW="60"
    >
      <div class="float-wrap">
        <div class="nav-box1">
          <div @mouseenter="toggleIsShow(true)" @mouseleave="toggleIsShow(false)" class="nav-item">
            <n-icon size="24" @mouseleave.stop="closefloat" class="icon-box">
              <svg width="24" height="24" xmlns="http://www.w3.org/2000/svg">
                <g fill="none" fill-rule="evenodd">
                  <path d="M0 0h24v24H0z" />
                  <path
                    d="M12 2.1c-5.468 0-9.9 4.432-9.9 9.9s4.432 9.9 9.9 9.9 9.9-4.432 9.9-9.9-4.432-9.9-9.9-9.9Zm0 1.164a8.736 8.736 0 1 1 0 17.472 8.736 8.736 0 0 1 0-17.472Zm4.837 10.505a.582.582 0 0 0-.795.212A4.663 4.663 0 0 1 12 16.315a4.663 4.663 0 0 1-4.042-2.333.582.582 0 1 0-1.007.582 5.827 5.827 0 0 0 5.05 2.914 5.827 5.827 0 0 0 5.048-2.914.582.582 0 0 0-.134-.741l-.078-.054ZM7.682 8.464a1.036 1.036 0 1 0 0 2.072 1.036 1.036 0 0 0 0-2.072Zm8.636 0a1.036 1.036 0 1 0 0 2.072 1.036 1.036 0 0 0 0-2.072Z"
                    fill="currentColor"
                    fill-rule="nonzero"
                  />
                </g>
              </svg>
            </n-icon>

            <div v-if="isShow" class="o-popup1" :class="{ show: isDynamic }">
              <n-icon size="24" :component="Close" class="icon-cancel" @click="cancelPopup" />
              <div class="slider">
                <p class="slider-title">
                  您对
                  <span class="title-name">openEuler测试平台</span>
                  的整体满意度如何
                </p>
                <div class="slider-body">
                  <n-space vertical>
                    <n-slider
                      :marks="marks"
                      :step="1"
                      :max="10"
                      v-model="score"
                      :on-update:value="handleInput"
                    />
                  </n-space>
                </div>
                <div class="grade-info">
                  <span>{{ infoData.grade1_1 }}</span>
                  <span>{{ infoData.grade2_1 }}</span>
                </div>
              </div>
              <div v-show="isReasonShow" class="reason">
                <div class="input-area" :class="{ 'is-focus': isFocuse }">
                  <textarea
                    ref="textareaRef"
                    v-model="inputText"
                    :placeholder="placeholder"
                    maxlength="500"
                  ></textarea>
                  <p>
                    <span>{{ inputText.length }}</span
                    >/500
                  </p>
                </div>
                <p class="more-info">
                  {{ infoData.more1
                  }}<a :href="infoData.more2Link" target="_blank">{{ infoData.more2 }} </a>
                </p>
                <div class="submit-btn">
                  <n-button size="medium" @click="handleClickSubmit">
                    {{ infoData.submit }}</n-button
                  >
                </div>
              </div>
            </div>
          </div>
          <div class="nav-item custom-box">
            <n-icon size="24" @mouseleave.stop="closefloat" class="icon-box">
              <svg width="24" height="24" xmlns="http://www.w3.org/2000/svg">
                <g fill="none" fill-rule="evenodd">
                  <path d="M0 0h24v24H0z" />
                  <path
                    d="M11.75 1.9c3.9 0 7.075 3.096 7.203 6.964l.004.243v4.99a6.975 6.975 0 0 1-6.975 6.974.6.6 0 1 1 0-1.2 5.775 5.775 0 0 0 5.771-5.553l.004-.222V9.107a6.007 6.007 0 0 0-12.01-.225l-.004.225v4.725a.6.6 0 0 1-1.192.097l-.008-.097V9.107A7.207 7.207 0 0 1 11.75 1.9Z"
                    fill="currentColor"
                    fill-rule="nonzero"
                  />
                  <path
                    d="M3.821 9.3c-1.06 0-1.921.86-1.921 1.921v2.643a1.921 1.921 0 1 0 3.843 0v-2.643c0-1.06-.86-1.921-1.922-1.921Zm0 1.2c.399 0 .722.323.722.721v2.643a.721.721 0 1 1-1.443 0v-2.643c0-.398.323-.721.721-.721ZM19.679 9.3c-1.062 0-1.922.86-1.922 1.921v2.643a1.921 1.921 0 1 0 3.843 0v-2.643c0-1.06-.86-1.921-1.921-1.921Zm0 1.2c.398 0 .721.323.721.721v2.643a.721.721 0 0 1-1.443 0v-2.643c0-.398.323-.721.722-.721ZM12.543 19.467h-1.586a1.004 1.004 0 1 0 0 2.009h1.586a1.004 1.004 0 1 0 0-2.009Zm-1.586.952h1.586a.053.053 0 0 1 0 .105h-1.586a.053.053 0 1 1 0-.105Z"
                    fill="currentColor"
                    fill-rule="nonzero"
                  />
                </g>
              </svg>
            </n-icon>

            <div class="o-popup2">
              <div
                v-for="item in floatData"
                :key="item.link"
                class="pop-item"
                rel="noopener noreferrer"
              >
                <n-icon size="32" v-if="item.id === 'robot'">
                  <svg
                    width="24px"
                    height="24px"
                    viewBox="0 0 24 24"
                    version="1.1"
                    xmlns="http://www.w3.org/2000/svg"
                    xmlns:xlink="http://www.w3.org/1999/xlink"
                  >
                    <title>icon/robot</title>
                    <g id="页面-1" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
                      <g
                        id="下载体验openEuler-赢开源三周年纪念礼包！"
                        transform="translate(-1823.000000, -1092.000000)"
                      >
                        <g id="编组-6" transform="translate(1810.000000, 977.000000)">
                          <g id="icon/robot" transform="translate(13.000000, 115.000000)">
                            <rect id="矩形" x="0" y="0" width="24" height="24"></rect>
                            <g id="icon-robot" transform="translate(1.000000, 1.000000)">
                              <rect
                                id="矩形"
                                stroke="#000000"
                                stroke-width="2"
                                x="3.3"
                                y="7.7"
                                width="15.4"
                                height="9.9"
                                rx="1"
                              ></rect>
                              <circle
                                id="椭圆形"
                                fill="#000000"
                                fill-rule="nonzero"
                                cx="7.7"
                                cy="12.1"
                                r="1.1"
                              ></circle>
                              <circle
                                id="椭圆形"
                                fill="#000000"
                                fill-rule="nonzero"
                                cx="14.3"
                                cy="12.1"
                                r="1.1"
                              ></circle>
                              <circle
                                id="椭圆形"
                                fill="#000000"
                                fill-rule="nonzero"
                                cx="11"
                                cy="2.2"
                                r="2.2"
                              ></circle>
                              <path
                                d="M-0.65,11.55 L2.85,11.55 C3.40228475,11.55 3.85,11.9977153 3.85,12.55 L3.85,12.75 C3.85,13.3022847 3.40228475,13.75 2.85,13.75 L-0.65,13.75 C-1.20228475,13.75 -1.65,13.3022847 -1.65,12.75 L-1.65,12.55 C-1.65,11.9977153 -1.20228475,11.55 -0.65,11.55 Z"
                                id="矩形"
                                fill="#000000"
                                fill-rule="nonzero"
                                transform="translate(1.100000, 12.650000) rotate(90.000000) translate(-1.100000, -12.650000) "
                              ></path>
                              <path
                                d="M19.15,11.55 L22.65,11.55 C23.2022847,11.55 23.65,11.9977153 23.65,12.55 L23.65,12.75 C23.65,13.3022847 23.2022847,13.75 22.65,13.75 L19.15,13.75 C18.5977153,13.75 18.15,13.3022847 18.15,12.75 L18.15,12.55 C18.15,11.9977153 18.5977153,11.55 19.15,11.55 Z"
                                id="矩形"
                                fill="#000000"
                                fill-rule="nonzero"
                                transform="translate(20.900000, 12.650000) rotate(90.000000) translate(-20.900000, -12.650000) "
                              ></path>
                              <path
                                d="M9.8,4.4 L12.2,4.4 C12.7522847,4.4 13.2,4.84771525 13.2,5.4 L13.2,5.6 C13.2,6.15228475 12.7522847,6.6 12.2,6.6 L9.8,6.6 C9.24771525,6.6 8.8,6.15228475 8.8,5.6 L8.8,5.4 C8.8,4.84771525 9.24771525,4.4 9.8,4.4 Z"
                                id="矩形"
                                fill="#000000"
                                fill-rule="nonzero"
                                transform="translate(11.000000, 5.500000) rotate(90.000000) translate(-11.000000, -5.500000) "
                              ></path>
                              <rect
                                id="矩形"
                                fill="#000000"
                                fill-rule="nonzero"
                                transform="translate(11.000000, 20.900000) rotate(-180.000000) translate(-11.000000, -20.900000) "
                                x="6.6"
                                y="19.8"
                                width="8.8"
                                height="2.2"
                                rx="1"
                              ></rect>
                            </g>
                          </g>
                        </g>
                      </g>
                    </g>
                  </svg>
                </n-icon>
                <n-icon size="32" v-if="item.id === 'forum'">
                  <svg id="icon-icon-chat_light" viewBox="0 0 32 32">
                    <path
                      fill="currentColor"
                      d="M20.068 20.030c2.535 0 4.591-2.051 4.591-4.58v-6.87c0-2.53-2.055-4.58-4.591-4.58h-11.477c-2.535 0-4.591 2.051-4.591 4.58v14.313c0 0.316 0.257 0.573 0.574 0.573 0.152-0.001 0.296-0.063 0.402-0.172l2.295-2.29c0.659-0.64 1.548-0.991 2.468-0.973h10.329zM6.295 18.885v-10.305c0-1.265 1.028-2.29 2.295-2.29h11.477c1.268 0 2.295 1.025 2.295 2.29v6.87c0 1.265-1.028 2.29-2.295 2.29h-10.329c-1.242 0-2.45 0.402-3.443 1.145zM26.954 8.58v9.16c0 2.53-2.055 4.58-4.591 4.58h-13.773c0 1.265 1.028 2.29 2.295 2.29h12.625c0.917-0.002 1.797 0.36 2.445 1.008l2.295 2.29c0.105 0.109 0.25 0.171 0.402 0.172 0.317 0 0.574-0.256 0.574-0.573v-16.637c0-1.256-1.014-2.277-2.272-2.29z"
                    ></path>
                  </svg>
                </n-icon>
                <n-icon size="32" v-if="item.id === 'quickIssue'">
                  <svg
                    width="24px"
                    height="24px"
                    viewBox="0 0 24 24"
                    version="1.1"
                    xmlns="http://www.w3.org/2000/svg"
                    xmlns:xlink="http://www.w3.org/1999/xlink"
                  >
                    <title>quickissue</title>
                    <g id="页面-1" stroke="none" stroke-width="1" fill="none" fill-rule="evenodd">
                      <g
                        id="下载体验openEuler-赢开源三周年纪念礼包！"
                        transform="translate(-1823.000000, -1041.000000)"
                      >
                        <g id="编组-6" transform="translate(1810.000000, 977.000000)">
                          <g id="quickissue" transform="translate(13.000000, 64.000000)">
                            <g id="编组" transform="translate(3.000000, 1.000000)" fill="#000000">
                              <polygon
                                id="Fill-1"
                                points="9.24670678 2.95555556e-05 4.70985511 2.61998178 4.70985511 18.7372173 9.24685456 21.3568001 13.7851101 18.7367001 13.7851101 12.8739123 11.2184318 10.6805946 11.2184318 17.2549323 9.24685456 18.3930429 7.27645956 17.2553018 7.27645956 4.10189733 9.24685456 2.963639 11.2184318 4.10226678 11.2184318 9.61984567 13.7851101 11.8130896 13.7851101 2.61998178 9.24692844 2.95555556e-05"
                              ></polygon>
                              <polygon
                                id="Fill-2"
                                points="14.457233 4.66620156 14.457233 8.042111 15.928213 6.785261 15.928213 14.5277821 14.457233 13.2709321 13.7851397 12.6965938 11.4232813 10.6786143 7.94865633 7.70968489 7.94865633 11.0856682 11.2183874 13.8793332 13.7851397 16.0725771 14.457233 16.6469154 15.6458836 17.6627399 18.4948913 16.018121 18.4948913 5.33866433 15.6153674 3.676386"
                              ></polygon>
                              <polygon
                                id="Fill-3"
                                points="0 5.33864956 0 16.0181062 2.84900778 17.6627251 4.03647611 16.6481568 4.03647611 13.2717301 2.56667833 14.5278412 2.56667833 6.78532011 4.03647611 8.040914 4.03647611 4.66493067 2.87945 3.67644511"
                              ></polygon>
                            </g>
                            <rect id="矩形" x="0" y="0" width="24" height="24"></rect>
                          </g>
                        </g>
                      </g>
                    </g>
                  </svg>
                </n-icon>
                <div class="text">
                  <p class="text-name">
                    <a :href="item.link" target="_blank">{{ item.text }}</a>
                  </p>
                  <p class="text-tip">{{ item.tip }}</p>
                </div>
              </div>
            </div>
          </div>
        </div>
        <n-popover trigger="hover" :show-arrow="false" placement="left">
          <template #trigger>
            <div class="nav-item nav-box1" style="margin-top: 12px">
              <p class="fix-item" @click="jumpToGitee">
                <n-icon size="24" color="#fff" style="margin-left: 3px; margin-top: -2px">
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
              </p>
            </div>
          </template>
          代码仓
        </n-popover>

        <div class="nav-box2">
          <div class="nav-item" @click="handleClickTop">
            <n-icon size="24" :component="UpToTop" />
          </div>
          <div class="nav-item custom-box" @click="backToBottom">
            <n-icon size="24" :component="DownToBottom" />
          </div>
        </div>
      </div>
    </vue3-draggable-resizable>
  </div>
</template>
<style lang="scss">
.n-slider-handle-indicator {
  padding: 0px 6px;
  font-size: 12px;
  background-color: #ffffff;
  color: #000000;
}
.n-slider-handle-indicator.n-slider-handle-indicator--top {
  margin-bottom: 3px !important;
}
.slider-body {
  .n-slider .n-slider-dots .n-slider-dot {
    height: 2px;
    width: 2px;
    background-color: rgba(0, 0, 0, 0.5);
    border: none;
  }
  .n-slider .n-slider-rail {
    background-color: #e5e5e5;
  }

  .n-slider .n-slider-rail .n-slider-rail__fill {
    background-image: linear-gradient(90deg, #62b2f6 0%, #002fa7 100%);
  }
  .n-slider .n-slider-dots .n-slider-dot.n-slider-dot--active {
    border: #ffffff;
    background-color: #ffffff;
  }
  .n-slider .n-slider-handles .n-slider-handle-wrapper .n-slider-handle {
    background-color: #002fa7;
    width: 8px;
    height: 8px;
    border: 6px solid #ffffff;
  }
}
</style>
<style lang="scss" scoped>
.float {
  position: fixed;
  right: 60px;
  bottom: 350px;
  z-index: 9;
  cursor: move;
  :deep(.dragwrapbox) {
    border-color: transparent;
    border-style: dashed;
    display: flex;
    justify-content: center;
    align-items: top;

    &:hover {
      border-color: #000;
      border-style: dashed;
    }

    .expandWrap {
      overflow: hidden;
      width: 40px;
      height: 50px;
    }
  }
  .float-wrap {
    // position: fixed;
    display: flex;
    flex-direction: column;
    // bottom: 200px;
    // right: 80px;
    // z-index: 10;
    .float-tip {
      position: absolute;
      width: 200px;
      top: 0;
      left: 0;
      background-color: #ffffff;
      padding: 16px;
      transform: translate(-42%, -110%);
      .tip-title {
        color: #000000;
        font-size: 16px;
      }
      .tip-detail {
        margin-top: 4px;
        font-size: 14px;
        color: #3f3f3f;
      }
      .btn-box {
        margin-top: 8px;
        display: flex;
        justify-content: flex-end;
        .o-button {
          font-size: 14px;
          border: none;
          padding: 0;
          color: #3f3f3f;
        }
      }
      &::after {
        display: block;
        content: '';
        width: 0;
        border-left: 8px solid transparent;
        border-top: 8px solid #ffffff;
        border-right: 8px solid transparent;
        border-bottom: 8px solid transparent;
        position: absolute;
        bottom: -14px;
        left: 50%;
      }
    }
    .nav-item {
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      width: 48px;
      height: 48px;
      background-color: #ffffff;
      background-size: cover;
      font-size: 12px;
      line-height: 18px;
      color: #000000;
      position: relative;
      cursor: pointer;
      &:hover {
        .icon-box {
          color: #002fa7;
        }
        .o-popup2 {
          transform: scale(1);
        }
      }
      .o-icon {
        font-size: 24px;
      }
      .o-popup1 {
        position: absolute;
        width: 360px;
        top: 0;
        right: 64px;
        background-color: #ffffff;
        padding: 16px 30px;
        transition: all 0.5s;
        transform: scale(0);
        transform-origin: 100% 50%;
        box-shadow: 0 1px 7px rgba(0, 0, 0, 0.3);
        cursor: default;
        &.show {
          transform: scale(1);
        }
        .icon-cancel {
          position: absolute;
          top: 5px;
          right: 10px;
          cursor: pointer;
          color: #000000;
        }
        .slider {
          .slider-title {
            font-size: 14px;
            line-height: 20px;
            color: #000000;
            text-align: center;
            white-space: nowrap;
            .title-name {
              font-weight: 600;
            }
          }

          .grade-info {
            width: 100%;
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: #707070;
            margin-top: -24px;
          }
        }
        .reason {
          margin-top: 16px;
          .input-area {
            border: 1px solid #e5e5e5;
            padding: 8px 16px;
            height: 88px;
            font-size: 12px;
            line-height: 18px;
            position: relative;
            &:hover {
              border: 1px solid #707070;
            }
            &.is-focus {
              border: 1px solid #707070;
            }
            textarea {
              width: 100%;
              height: 100%;
              border: none;
              outline: none;
              resize: none;
              background-color: #ffffff;
              color: #000000;
            }
            p {
              text-align: right;
              color: #707070;
              position: absolute;
              right: 6px;
              bottom: 6px;
            }
          }
          .more-info {
            margin-top: 8px;
            color: #707070;
            font-size: 12px;
            line-height: 18px;
          }
          .submit-btn {
            margin-top: 16px;
            text-align: center;
            :deep(.o-button) {
              border-color: #707070;
              color: #000000;
              &:hover {
                border-color: #002fa7;
                background-color: #002fa7;
                color: #ffffff;
              }
            }
          }
        }
      }
      .o-popup2 {
        position: absolute;
        top: 0;
        right: 64px;
        width: 240px;
        padding: 24px;
        background-color: #ffffff;
        transition: all 0.5s;
        transform: scale(0);
        transform-origin: 100% 50%;
        box-shadow: 0 1px 7px rgba(0, 0, 0, 0.3);
        cursor: default;
        .pop-item {
          display: flex;
          color: #000000;
          & ~ .pop-item {
            margin-top: 18px;
          }

          .text {
            margin-left: 12px;
            text-align: left;
            .text-name {
              font-size: 14px;
              line-height: 32px;
              font-weight: 600;
              margin: 0;
              a {
                color: #000000;
                &:hover {
                  color: #002fa7;
                }
              }
            }
            .text-tip {
              font-size: 12px;
              line-height: 18px;
              color: #3f3f3f;
              margin: 0;
            }
          }
        }
      }

      .fix-item {
        background: #000;
        display: flex;
        justify-content: center;
        align-items: center;
        border-radius: 50%;
        overflow: hidden;
        height: 24px;
        width: 24px;
        transition: all 1s;
      }
    }
    .custom-box::before {
      display: block;
      content: '';
      height: 1px;
      width: 16px;
      background-color: #e5e8f0;
      position: absolute;
      left: 50%;
      top: 0;
      transform: translate(-50%);
    }
    .nav-box1 {
      box-shadow: 0 1px 7px rgba(0, 0, 0, 0.3);
    }
    .nav-box2 {
      margin-top: 12px;
      box-shadow: 0 1px 7px rgba(0, 0, 0, 0.3);
      opacity: 0.6;
      .nav-item {
        background-color: #ffffff;
        opacity: 0.3;
        &:hover {
          opacity: 1;
        }
      }
      &:hover {
        opacity: 1;
      }
    }
    .nav-box1:hover {
      .fix-item {
        background: rgba(0, 47, 167, 1);
      }
    }
  }
}
</style>
