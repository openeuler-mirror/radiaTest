import { createRouter, createWebHistory } from 'vue-router';
import Home from '@/views/home/Home';
import Dashboard from '@/views/dashboard/Dashboard';
import Product from '@/views/product/Product';
import Milestone from '@/views/milestone/Milestone';
import Pmachine from '@/views/pmachine/Pmachine';
import Vmachine from '@/views/vmachine/Vmachine';
import Template from '@/views/template/Template';
import Job from '@/views/job/Job';
import Testcase from '@/views/caseManage/testcase/Testcase';
import Blank from '@/components/public/Blank';
import Report from '@/views/taskManage/report/Report.vue';
import TaskManage from '@/views/taskManage/TaskManage';
import Task from '@/views/taskManage/task/Task';
import Distribution from '@/views/taskManage/distribution/Distribution.vue';
// import Login from '@/views/login/Login.vue';
import newLogin from '@/views/login/newLogin.vue';
import PersonalCenter from '@/views/personalCenter/PersonalCenter.vue';
import AccountManagement from '@/views/personalCenter/accountManagement/AccountManagement.vue';
import AccountInfo from '@/views/personalCenter/accountInfo/AccountInfo.vue';
import News from '@/views/personalCenter/news/News.vue';
import OrgManagement from '@/views/personalCenter/orgManagement/orgManagement.vue';
import CaseManagement from '@/views/caseManage/CaseManagement.vue';

const routerHistory = createWebHistory();
const router = createRouter({
  history: routerHistory,
  routes: [
    {
      path: '/',
      redirect: '/login',
    },
    {
      path: '/home/',
      redirect: '/home/dashboard',
      component: Home,
      name: 'home',
      meta: {
        title: 'raidaTest测试平台'
      },
      children: [
        {
          path: 'dashboard/',
          component: Dashboard,
          meta: {
            title: 'raidaTest测试平台'
          }
        },
        {
          path: 'pvm/',
          redirect: '/home/pvm/milestone',
          component: Blank,
          children: [
            {
              path: 'product/',
              component: Product,
              meta: {
                title: '产品版本管理'
              },
            },
            {
              path: 'milestone/',
              component: Milestone,
              meta: {
                title: '里程碑管理'
              },
            },
          ]
        },
        {
          path: 'resource-pool/',
          redirect: '/home/resource-pool/vmachine',
          component: Blank,
          children: [
            {
              path: 'pmachine/',
              component: Pmachine,
              meta: {
                title: '物理机资源池'
              },
            },
            {
              path: 'vmachine/',
              component: Vmachine,
              meta: {
                title: '虚拟机资源池'
              },
            },
          ]
        },
        {
          path: 'testing/',
          redirect: '/home/testing/jobs',
          component: Blank,
          children: [
            {
              path: 'jobs/',
              component: Job,
              meta: {
                title: '测试看板'
              },
            },
            {
              path: 'template/',
              component: Template,
              meta: {
                title: '模板仓库'
              },
            },
          ]
        },
        {
          path: 'tcm/',
          redirect: '/home/tcm/testcase',
          component: CaseManagement,
          meta: {
            title: '用例管理'
          },
          children: [
            {
              path: 'testcase/',
              component: Testcase,
            },
          ]
        },
        {
          path: 'tm/',
          redirect: '/home/tm/task',
          component: TaskManage,
          children: [
            {
              path: 'task/',
              component: Task,
            },
            {
              path: 'report/',
              component: Report,
            },
            {
              path: 'distribution/',
              component: Distribution,
            },
          ]
        },
      ]
    },
    {
      path: '/login/',
      component: newLogin,
      name: 'login',
      meta: {
        title: '登陆'
      }
    },
    {
      path: '/personalCenter/',
      component: PersonalCenter,
      name: 'PersonalCenter',
      children: [
        {
          path: '',
          redirect: '/personalCenter/accountManagement/'
        },
        {
          path: 'accountManagement/',
          component: AccountManagement,
          name: 'accountManagement',
          meta: {
            title: '账号管理',
          },
        },
        {
          path: 'accountInfo/',
          component: AccountInfo,
          name: 'accountInfo',
          meta: {
            title: '基本信息',
          },
        },
        {
          path: 'orgManagement/',
          component: OrgManagement,
          name: 'orgManagement',
          meta: {
            title: '组织管理'
          }
        },
        {
          path: 'news/',
          component: News,
          name: 'news',
          meta: {
            title: '消息中心'
          },
        }
      ]
    },
  ]
});
export default router;
