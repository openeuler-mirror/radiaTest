import { createRouter, createWebHistory } from 'vue-router';
import Home from '@/views/home/Home';
import Dashboard from '@/views/dashboard/Dashboard';
import Product from '@/views/product/Product';
import Milestone from '@/views/milestone/Milestone';
import Pmachine from '@/views/pmachine/Pmachine';
import Vmachine from '@/views/vmachine/Vmachine';
import Template from '@/views/testCenter/template/Template';
import TestCenterManagement from '@/views/testCenter/TestCenterManagement.vue';
import Job from '@/views/testCenter/job/Job';
import Testcase from '@/views/caseManage/testcase/Testcase';
import Blank from '@/components/public/Blank';
import Report from '@/views/taskManage/report/Report.vue';
import TaskManage from '@/views/taskManage/TaskManage';
import Task from '@/views/taskManage/task/Task';
import Distribution from '@/views/taskManage/distribution/Distribution.vue';
import newLogin from '@/views/login/newLogin.vue';
import PersonalCenter from '@/views/personalCenter/PersonalCenter.vue';
import AccountManagement from '@/views/personalCenter/accountManagement/AccountManagement.vue';
import AccountInfo from '@/views/personalCenter/accountInfo/AccountInfo.vue';
import News from '@/views/personalCenter/news/News.vue';
import OrgManagement from '@/views/personalCenter/orgManagement/orgManagement.vue';
import authorityManagement from '@/views/personalCenter/authorityManagement/authorityManagement.vue';
import CaseManagement from '@/views/caseManage/CaseManagement.vue';
import folderView from '@/views/caseManage/folderView/folderView.vue';
import taskDetails from '@/views/caseManage/folderView/taskDetails/taskDetails.vue';
import frameWork from '@/views/caseManage/frameWork/frameWork.vue';
import orgNode from '@/views/caseManage/folderView/orgNodes/orgNodes.vue';
import termNode from '@/views/caseManage/folderView/termNodes/termNodes.vue';
import testsuite from '@/views/caseManage/testsuite/testsuite.vue';
import rulesManagement from '@/views/personalCenter/authorityManagement/rulesManagement/rulesManagement.vue';
import rolesManagement from '@/views/personalCenter/authorityManagement/rolesManagement/rolesManagement.vue';
import usersManagement from '@/views/personalCenter/usersManagement/usersManagement.vue';
import caseReview from '@/views/caseManage/caseReview/caseReview.vue';
import caseReviewDetail from '@/views/caseManage/caseReviewDetail/caseReviewDetail.vue';
import resourcePool from '@/views/resourcePool/resourcePool.vue';
import versionManagement from '@/views/versionManagement/versionManagement.vue';
import product from '@/views/versionManagement/product/product.vue';
import NotFound from '@/views/resultPage/NotFound.vue';

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
        title: 'raidaTest????????????',
      },
      children: [
        {
          path: 'dashboard/',
          component: Dashboard,
          meta: {
            title: 'raidaTest????????????',
          },
        },
        {
          path: 'versionManagement/',
          component: versionManagement,
          redirect: '/home/versionManagement/product',
          name:'versionManagement',
          meta: {
            title:'????????????'
          },
          children: [
            { path: 'product/', name: 'product', component: product}
          ]
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
                title: '??????????????????',
              },
            },
            {
              path: 'milestone/',
              component: Milestone,
              meta: {
                title: '???????????????',
              },
            },
          ],
        },
        {
          path: 'resource-pool/',
          redirect: '/home/resource-pool/vmachine',
          component: Blank,
          children: [
            {
              path: 'management/',
              component: resourcePool,
              name: 'resourcePool',
              children: [
                {
                  path: 'pmachine/:machineId',
                  component: Pmachine,
                  name: 'pmachine',
                },
                {
                  path: 'vmachine/:machineId',
                  component: Vmachine,
                  name: 'vmachine',
                },
              ],
              meta: {
                title: '???????????????',
              },
            },
            {
              path: 'pmachine/',
              component: Pmachine,
              meta: {
                title: '??????????????????',
              },
            },
            {
              path: 'vmachine/',
              component: Vmachine,
              meta: {
                title: '??????????????????',
              },
            },
          ],
        },
        {
          path: 'testing/',
          redirect: '/home/testing/jobs',
          component: TestCenterManagement,
          children: [
            {
              path: 'jobs/',
              component: Job,
              meta: {
                title: '????????????',
              },
            },
            {
              path: 'template/',
              component: Template,
              meta: {
                title: '????????????',
              },
            },
          ],
        },
        {
          path: 'tcm/',
          redirect: '/home/tcm/testcase',
          component: CaseManagement,
          meta: {
            title: '????????????',
          },
          children: [
            {
              path: 'case-review/',
              component: caseReview,
              name: 'caseReview',
            },
            {
              path: 'case-review-detail/:commitId',
              component: caseReviewDetail,
              name: 'caseReviewDetail',
            },
            {
              path: 'testcase/',
              component: Testcase,
              name: 'testcase',
            },
            {
              path: 'testsuite/',
              component: testsuite,
              name: 'testsuite',
            },
            {
              path: 'folderview/',
              component: folderView,
              name: 'folderview',
              children: [
                {
                  path: 'node-detail/:taskid/',
                  component: taskDetails,
                  name: 'taskDetails',
                },
                {
                  path: 'org-node',
                  component: orgNode,
                  name: 'orgNode',
                },
                {
                  path: 'term-node',
                  component: termNode,
                  name: 'termNode',
                },
              ],
            },
            {
              path: 'framework',
              component: frameWork,
              name: 'frameWork',
            },
          ],
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
          ],
        },
      ],
    },
    {
      path: '/login/',
      component: newLogin,
      name: 'login',
      meta: {
        title: '??????',
      },
    },
    {
      path: '/personal-center/',
      component: PersonalCenter,
      name: 'PersonalCenter',
      children: [
        {
          path: '',
          redirect: '/personal-center/account-management/',
        },
        {
          path: 'account-management/',
          component: AccountManagement,
          name: 'accountManagement',
          meta: {
            title: '????????????',
          },
        },
        {
          path: 'account-info/',
          component: AccountInfo,
          name: 'accountInfo',
          meta: {
            title: '????????????',
          },
        },
        {
          path: 'org-management/',
          component: OrgManagement,
          name: 'orgManagement',
          meta: {
            title: '????????????',
          },
        },
        {
          path: 'authority-management/',
          component: authorityManagement,
          name: 'authorityManagement',
          children: [
            {
              path: 'rules-management/',
              component: rulesManagement,
              name: 'rulesManagement',
            },
            {
              path: 'roles-management/:roleId',
              component: rolesManagement,
              name: 'rolesManagement',
            },
          ],
          meta: {
            title: '????????????',
          },
        },
        {
          path: 'users-management/',
          component: usersManagement,
          name: 'usersManagement',
          meta: {
            title: '????????????',
          },
        },
        {
          path: 'news/',
          component: News,
          name: 'news',
          meta: {
            title: '????????????',
          },
        },
      ],
    },
    {
      path: '/:catchAll(.*)',
      component: NotFound,
      name: 'NotFound',
    }
  ],
});
export default router;
