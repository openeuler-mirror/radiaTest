import { requestClient } from '#/api/request';

export interface FeishuAppConfig {
  app_id: string;
  created_at: string;
  environment: string;
  has_app_secret: boolean;
  id: string;
  is_enabled: boolean;
  updated_at: string;
}

export interface FeishuAppConfigPayload {
  app_id: string;
  app_secret: string;
  is_enabled: boolean;
}

export interface FeishuIdentity {
  created_at: string;
  id: string;
  open_id: string;
  provider: string;
  union_id: null | string;
  updated_at: string;
  user_id: string;
}

export interface FeishuBindUrl {
  authorize_url: string;
}

export async function getFeishuAppConfigApi() {
  return requestClient.get<FeishuAppConfig | null>('/integrations/feishu/app');
}

export async function upsertFeishuAppConfigApi(
  payload: FeishuAppConfigPayload,
) {
  return requestClient.request<FeishuAppConfig>('/integrations/feishu/app', {
    data: payload,
    method: 'PUT',
  });
}

export async function getMyFeishuIdentityApi() {
  return requestClient.get<FeishuIdentity | null>(
    '/integrations/feishu/me/identity',
  );
}

export async function getMyFeishuBindUrlApi(redirectUri: string) {
  return requestClient.get<FeishuBindUrl>('/integrations/feishu/me/bind-url', {
    params: { redirect_uri: redirectUri },
  });
}
