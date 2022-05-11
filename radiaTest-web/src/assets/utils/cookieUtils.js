export function getCookieValByKey (key) {
  const cookieStr = document.cookie;
  const cookies = cookieStr.split(';');
  const cookieObj = {};
  for (const item of cookies) {
    const _key = item.slice(0, item.indexOf('=')).trim();
    const value = item.slice(item.indexOf('=')+1);
    cookieObj[_key] = value;
  }
  return cookieObj[key]?.trim();
}
