import { requestClient } from '#/api/request';

export namespace AuthApi {
  /** 登录接口参数 */
  export interface LoginParams {
    password?: string;
    username?: string;
  }

  /** 登录接口返回值 */
  export interface LoginResult {
    accessToken: string;
  }

  export interface LoginResponse {
    access_token: string;
    token_type: string;
  }
}

/**
 * 登录
 */
export async function loginApi(data: AuthApi.LoginParams) {
  const response = await requestClient.post<AuthApi.LoginResponse>(
    '/auth/login',
    data,
  );
  return {
    accessToken: response.access_token,
  };
}

export async function refreshTokenApi(): Promise<{ data: string }> {
  throw new Error('Refresh token is not enabled');
}

export function logoutApi() {
  // JWT 会话只保存在浏览器端，退出时无需调用后端。
}
