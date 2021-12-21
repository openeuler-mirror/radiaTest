const handleMenuClick = () => {
  document.getElementById('header').style.height = '400px';
};
const handleMenuBlur = () => {
  document.getElementById('header').style.height = '100px';
};

export {
  handleMenuBlur,
  handleMenuClick,
};
