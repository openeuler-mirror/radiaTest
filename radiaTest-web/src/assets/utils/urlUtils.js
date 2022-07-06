function openChildWindow (url, width = 800, height = 600) {
  const left = (window.screen.width - width) / 2;
  const top = (window.screen.height - height) / 2;
  window.open(url, 'radiatestChildWindow', `width=${width},height=${height},top=${top},left=${left}`);
}

function urlArgs () {
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

export {
  openChildWindow, urlArgs,
};
