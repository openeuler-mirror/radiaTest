export interface LatestRequest {
  commit(callback: () => void): void;
}

export function createLatestRequestGuard() {
  let latestRequestId = 0;

  return {
    begin(): LatestRequest {
      const requestId = ++latestRequestId;
      return {
        commit(callback) {
          if (requestId === latestRequestId) callback();
        },
      };
    },
    invalidate() {
      latestRequestId += 1;
    },
  };
}
