import * as details from './details';
import * as comment from './comment';
import * as content from './content';
import { init } from '@/views/taskManage/task/modules/taskDetail';
export const modules = {
  ...details,
  ...comment,
  ...content,
  init
};
