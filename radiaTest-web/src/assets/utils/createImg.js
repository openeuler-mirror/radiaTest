// 获取字符串的哈希值
const getHashCode = (str, caseSensitive) => {
  let hash = 1315423911;
  let i;
  let ch;
  let tempStr;
  if (!caseSensitive) {
    tempStr = str.toLowerCase();
  } else {
    tempStr = str;
  }

  for (i = tempStr.length - 1; i >= 0; i--) {
    ch = tempStr.charCodeAt(i);
    hash ^= (hash << 5) + ch + (hash >> 2);
  }
  return hash & 0x7fffffff;
};

const getColor = (value) => {
  return `#${getHashCode(value).toString(16).substring(0, 6)}`;
};

const createAvatar = (text, size = 40, textColor = '#fff', backgoundColor) => {
  let bgColor = backgoundColor ? backgoundColor : getColor(text);
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  ctx.font = `${size / 2}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = bgColor;
  ctx.fillRect(0, 0, size, size);
  ctx.fillStyle = textColor;
  ctx.fillText(text, size / 2, size / 2);
  return canvas.toDataURL('image/jpeg');
};

export { createAvatar };
