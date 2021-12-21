import router from '@/router/index';

function gotoNews () {
  router.push({
    name: 'news'
  });
}

export {
  gotoNews,
};
