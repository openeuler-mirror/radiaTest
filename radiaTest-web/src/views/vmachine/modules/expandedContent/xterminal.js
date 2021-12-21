import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';

const createTerminal = (term, fitAddon, terminalSocket, props) => {
  const terminalContainer = document.getElementById('xterm-viewer');

  term.value = new Terminal({
    rendererType: 'canvas',
    cursorStyle: 'block',
    cursorBlink: true,
    convertEol: true,
    disableStdin: false,
    scrollback: 800,
    theme: {
      foreground: 'white',
      background: '#060101',
    },
    fontSize: 18,
  });
  fitAddon.value = new FitAddon();
  term.value.loadAddon(fitAddon.value);
  term.value.open(terminalContainer);
  fitAddon.value.fit();

  term.value.onData((key) => {
    terminalSocket.emit('command', { command: key });
  });

  terminalSocket.listen(props.ip, (data) => {
    term.value.write(data);
  });

  terminalSocket.emit('start', {
    machine_ip: props.ip,
    hostname: props.ip,
    port: props.port,
    username: props.user,
    password: props.passwd,
    cols: term.value.cols,
    rows: term.value.rows,
  });
  term.value.focus();
};

export default {
  createTerminal,
};
