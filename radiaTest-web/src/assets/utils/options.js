import { getRepo } from '@/api/get';
export async function createRepoOptions(filter) {
  const data = await getRepo(filter);
  return data.data.map((item) => ({
    label: item.git_url,
    value: String(item.id),
  }));
}
