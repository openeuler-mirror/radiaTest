// YYYY-MM-DD HH:mm:ss
const any2standard = (origin) => new Date(origin).toLocaleString('zh-CN', { hourCycle: 'h23' }).replace(/\//g, '-');

// 时间戳
const any2stamp = (origin) => new Date(origin).getTime();

// 自定义时间格式
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
    S: time.getMilliseconds()
  };
  if (/(y+)/g.test(formatString)) {
    formatString = formatString.replace(RegExp.$1, `${time.getFullYear()}`.substr(4 - RegExp.$1.length));
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
const timeMenu = {
  us: {
    next: 'ms',
    step: 1000
  },
  ms: {
    next: 's',
    step: 1000
  },
  s: {
    next: 'min',
    step: 60
  },
  min: {
    next: 'h',
    step: 60
  },
  h: {
    next: ''
  }
};

// 计算时间长度
function timeProcess(time, unit) {
  const nextUnit = timeMenu[unit.toLowerCase()].next;
  const nextUnitTime = Number(time) / timeMenu[unit.toLowerCase()].step;
  if (nextUnitTime >= 1 && nextUnit) {
    return timeProcess(nextUnitTime, nextUnit);
  }
  return Number(time).toFixed(2) + unit;
}

export { any2stamp, timeProcess, any2standard, formatTime };
