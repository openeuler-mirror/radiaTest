interface VNCConsoleConfig {
  password: null | string;
}

export function buildVNCOptions(consoleConfig: VNCConsoleConfig) {
  return {
    ...(consoleConfig.password
      ? { credentials: { password: consoleConfig.password } }
      : {}),
    wsProtocols: ['binary'],
  };
}
