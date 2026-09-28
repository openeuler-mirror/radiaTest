declare module '@novnc/novnc' {
  interface RFBCredentials {
    password?: string;
    target?: string;
    username?: string;
  }

  interface RFBOptions {
    credentials?: RFBCredentials;
    repeaterID?: string;
    shared?: boolean;
    wsProtocols?: string[];
  }

  export default class RFB extends EventTarget {
    clipViewport: boolean;
    focusOnClick: boolean;
    resizeSession: boolean;
    scaleViewport: boolean;
    viewOnly: boolean;

    constructor(
      target: HTMLElement,
      urlOrChannel: string,
      options?: RFBOptions,
    );

    disconnect(): void;
    focus(): void;
    sendCtrlAltDel(): void;
    sendKey(keysym: number, code: null | string, down?: boolean): void;
  }
}
