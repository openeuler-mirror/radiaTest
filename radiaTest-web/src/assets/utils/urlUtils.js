function urlArgs() {
  const args = {};
  const query = location.search.substring(1);
  const pairs = query.split('&');
  for (let i = 0; i < pairs.length; i++) {
    const pos = pairs[i].indexOf('=');
    if (pos !== -1) {
      const name = pairs[i].substring(0, pos);
      const value = pairs[i].substring(pos + 1);
      args[name] = value;
    }
  }
  return args;
}
function resUrlArgs(resUrl) {
  const args = {};
  const urlObj = new URL(resUrl);
  const query = urlObj.search.substring(1);
  const pairs = query.split('&');
  for (let i = 0; i < pairs.length; i++) {
    const pos = pairs[i].indexOf('=');
    if (pos !== -1) {
      const name = pairs[i].substring(0, pos);
      const value = pairs[i].substring(pos + 1);
      args[name] = value;
    }
  }
  return args;
}
export { urlArgs, resUrlArgs };
