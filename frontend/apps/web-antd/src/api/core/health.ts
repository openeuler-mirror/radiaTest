import { requestClient } from '#/api/request';

interface DatabaseHealth {
  database: string;
  status: string;
}

export async function getDatabaseHealthApi() {
  return requestClient.get<DatabaseHealth>('/health/database');
}
