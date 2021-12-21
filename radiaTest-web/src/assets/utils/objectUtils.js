const removeKey = (thisObject, target) => {
  return Object.keys(thisObject).filter(
    key => key !== target
  ).reduce(
    (obj, key) => {
      obj[key] = thisObject[key];
      return obj;
    }, {});
};

export {
  removeKey,
};
