const vmachineClick = (router) => {
  router.push('/home/resource-pool/vmachine');
};
const jobClick = (router) => {
  router.push('/home/testing/jobs');
};
const handleGiteeClick = () => {
  window.open('https://gitee.com/lemon-higgins/mugen');
};

export {
  vmachineClick,
  jobClick,
  handleGiteeClick,
};
