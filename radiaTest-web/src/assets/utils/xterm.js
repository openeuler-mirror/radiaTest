import { Terminal } from 'xterm';
export function createTerminal() {
  return new Terminal({
    rendererType: 'canvas', //渲染类型
    convertEol: true, //启用时，光标将设置为下一行的开头
    scrollback: 10, //终端中的回滚量
    disableStdin: false, //是否应禁用输入。
    cursorStyle: 'underline', //光标样式
    cursorBlink: true, //光标闪烁
    theme: {
      foreground: '#ffffff', //字体
      background: '#000000', //背景色
      cursor: 'help', //设置光标
    },
  });
}
