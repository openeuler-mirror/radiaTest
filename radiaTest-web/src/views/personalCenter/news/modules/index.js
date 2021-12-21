import * as readNews from './readNews';
import * as unreadNews from './unreadNews';
import { showLoading } from '@/assets/utils/loading';

export const modules = { ...readNews, ...unreadNews, showLoading };
