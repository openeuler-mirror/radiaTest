const show = (cols) => {
  cols.value.unshift({
    type: 'selection',
  });
};
const off = (cols) => {
  cols.value.shift();
};
export default {
  show,
  off,
};
