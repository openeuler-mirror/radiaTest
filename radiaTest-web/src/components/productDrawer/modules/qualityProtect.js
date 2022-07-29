const handleMouseEnter = (id) => {
  document.getElementById(id).style.boxShadow = '0px 0px 20px #f3f3f3';
};

const handleMouseLeave = (id) => {
  document.getElementById(id).style.boxShadow = 'none';
};

export {
  handleMouseEnter,
  handleMouseLeave,
};
