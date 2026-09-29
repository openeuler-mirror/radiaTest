export type DisconnectedConsoleStatus =
  | 'destroyed'
  | 'disconnected'
  | 'stopped';

export function disconnectedConsoleStatus(
  powerState: string,
): DisconnectedConsoleStatus {
  if (powerState === 'destroyed') return 'destroyed';
  if (powerState === 'shut off') return 'stopped';
  return 'disconnected';
}
