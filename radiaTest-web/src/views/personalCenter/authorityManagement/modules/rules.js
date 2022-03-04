import router from '@/router';
import { setActiveRole } from './role';

function rulesView() {
  setActiveRole('');
  router.push({ name: 'rulesManagement' });
}

export { rulesView };
