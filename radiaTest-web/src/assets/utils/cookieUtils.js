export function getCookieValByKey (key) {
  const cookieStr = document.cookie;
  const cookies = cookieStr.split(';');
  const cookieObj = {};
  for (const item of cookies) {
    const element = item.split('=');
    [, cookieObj[element[0].trim()]] = element;
  }
  return cookieObj[key]?.trim();
}
