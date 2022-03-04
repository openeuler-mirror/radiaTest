const any2standard = (origin) =>
  new Date(origin)
    .toLocaleString('zh-CN', { hourCycle: 'h23' })
    .replace(/\//g, '-');

const any2stamp = (origin) => new Date(origin).getTime();

function formatTime(date, formatStr) {
  let formatString = formatStr;
  if (!date) {
    return '';
  }
  const time = new Date(date);
  const o = {
    'M+': time.getMonth() + 1,
    'd+': time.getDate(),
    'h+': time.getHours(),
    'm+': time.getMinutes(),
    's+': time.getSeconds(),
    'q+': Math.floor((time.getMonth() + 3) / 3),
    S: time.getMilliseconds(),
  };
  if (/(y+)/g.test(formatString)) {
    formatString = formatString.replace(
      RegExp.$1,
      `${time.getFullYear()}`.substr(4 - RegExp.$1.length)
    );
  }
  for (let k in o) {
    if (new RegExp(`(${k})`).test(formatString)) {
      formatString = formatString.replace(
        RegExp.$1,
        RegExp.$1.length === 1 ? o[k] : `00${o[k]}`.substr(`${o[k]}`.length)
      );
    }
  }
  return formatString;
}

export { any2stamp, any2standard, formatTime };
