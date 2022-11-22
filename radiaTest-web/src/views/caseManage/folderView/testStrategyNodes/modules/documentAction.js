import { ref } from 'vue';

const documentList = ref([
  { id: '1', title: 'NestOS 22.03 LTS 版本测试策略', iframeUrl: 'https://www.baidu.com/' },
  { id: '2', title: 'OpenEuler 22.03 LTS 版本测试策略版本测试策略版本测试策略版本测试策略', iframeUrl: 'https://www.baidu.com/' },
  { id: '3', title: 'NestOS 22.03 LTS 版本测试策略', iframeUrl: 'https://www.baidu.com/' },
  { id: '4', title: 'NestOS 22.03 LTS 版本测试策略', iframeUrl: 'https://www.baidu.com/' },
]);

function documentInit() {
  //
  console.log('asffasfafas');
}

export {
  documentList,
  documentInit,
};
