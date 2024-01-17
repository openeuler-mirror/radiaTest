import { createRouter, createWebHistory } from 'vue-router';
import Home from '@/views/home/Home';
import Dashboard from '@/views/dashboard/Dashboard';
import Testcase from '@/views/caseManage/testcase/Testcase';
import Report from '@/views/taskManage/report/Report.vue';
import Task from '@/views/taskManage/task/Task';
import Require from '@/views/taskManage/require/Require.vue';
import StrategyCenter from '@/views/strategyCenter/StrategyCenter';
import Distribution from '@/views/taskManage/distribution/Distribution.vue';
import PersonalCenter from '@/views/personalCenter/PersonalCenter.vue';
import AccountManagement from '@/views/personalCenter/accountManagement/AccountManagement.vue';
import AccountInfo from '@/views/personalCenter/accountInfo/AccountInfo.vue';
import News from '@/views/personalCenter/news/News.vue';
import OrgManagement from '@/views/personalCenter/orgManagement/orgManagement.vue';
import authorityManagement from '@/views/personalCenter/authorityManagement/authorityManagement.vue';
import CaseManagement from '@/views/caseManage/CaseManagement.vue';
import folderView from '@/views/caseManage/folderView/folderView.vue';
import testcaseNodes from '@/views/caseManage/folderView/testcaseNodes/testcaseNodes.vue';
import orgNode from '@/views/caseManage/folderView/orgNodes/orgNodes.vue';
import termNode from '@/views/caseManage/folderView/termNodes/termNodes.vue';
import casesetNode from '@/views/caseManage/folderView/casesetNodes/casesetNodes.vue';
import baselineNode from '@/views/caseManage/folderView/baselineNodes/baselineNodes.vue';
import suiteNode from '@/views/caseManage/folderView/suiteNodes/suiteNodes.vue';
import testsuite from '@/views/caseManage/testsuite/testsuite.vue';
import rulesManagement from '@/views/personalCenter/authorityManagement/rulesManagement/rulesManagement.vue';
import rolesManagement from '@/views/personalCenter/authorityManagement/rolesManagement/rolesManagement.vue';
import usersManagement from '@/views/personalCenter/usersManagement/usersManagement.vue';
import configManagement from '@/views/personalCenter/configManagement.vue';
import securitySetting from '@/views/personalCenter/securitySetting.vue';
import versionManagement from '@/views/versionManagement/versionManagement.vue';
import Product from '@/views/versionManagement/product/product.vue';
import Milestone from '@/views/versionManagement/milestone/milestone.vue';
import NotFound from '@/views/resultPage/NotFound.vue';
import AtDetail from '@/views/atDetail/index.vue';
import PersonalBoard from '@/views/taskManage/personalBoard/PersonalBoard';

const routerHistory = createWebHistory();
const router = createRouter({
  history: routerHistory,
  routes: [
    {
      path: '/',
      redirect: '/home'
    },
    {
      path: '/at-detail',
      component: AtDetail,
      name: 'atDetail',
      meta: {
        title: 'EulerTest'
      }
    },
    {
      path: '/home/',
      redirect: '/home/workdesk',
      component: Home,
      name: 'home',
      meta: {
        title: 'EulerTest'
      },
      children: [
        {
          path: 'workdesk',
          component: Dashboard,
          redirect: { name: 'dashboard' },
          meta: {
            title: 'EulerTest'
          },
          children: [
            {
              path: 'dashboard/',
              component: PersonalBoard,
              name: 'dashboard'
            },
            {
              path: 'task/',
              component: Task,
              name: 'task'
            },
            {
              path: 'require/',
              component: Require,
              name: 'require'
            },
            {
              path: 'report/',
              component: Report,
              name: 'report'
            },
            {
              path: 'distribution/',
              component: Distribution,
              name: 'distribution'
            },
            {
              path: 'design/',
              component: StrategyCenter,
              name: 'design'
            }
          ]
        },
        {
          path: 'product-version',
          redirect: { name: 'vmProduct' },
          component: versionManagement,
          children: [
            {
              path: 'product/',
              component: Product,
              name: 'vmProduct',
              meta: {
                title: 'EulerTest'
              }
            },
            {
              path: 'milestone/',
              component: Milestone,
              name: 'vmMilestone',
              meta: {
                title: 'EulerTest'
              }
            }
          ]
        },
        {
          path: 'testcase',
          redirect: { name: 'folderview' },
          component: CaseManagement,
          meta: {
            title: 'EulerTest'
          },
          children: [
            {
              path: 'testcase/',
              component: Testcase,
              name: 'testcase'
            },
            {
              path: 'testsuite/',
              component: testsuite,
              name: 'testsuite'
            },
            {
              path: 'folderview/',
              component: folderView,
              name: 'folderview',
              children: [
                {
                  path: 'org-node/:taskId/',
                  component: orgNode,
                  name: 'orgNode'
                },
                {
                  path: 'term-node/:taskId/',
                  component: termNode,
                  name: 'termNode'
                },
                {
                  path: 'caseset-node/:taskId/',
                  component: casesetNode,
                  name: 'casesetNode'
                },
                {
                  path: 'baseline-node/:taskId/',
                  component: baselineNode,
                  name: 'baselineNode'
                },
                {
                  path: 'suite-node/:taskId/:suiteId',
                  component: suiteNode,
                  name: 'suiteNode'
                },
                {
                  path: 'testcase-node/:taskId/:caseId',
                  component: testcaseNodes,
                  name: 'testcaseNodes'
                }
              ]
            }
          ]
        }
      ]
    },
    {
      path: '/personal-center/',
      component: PersonalCenter,
      name: 'PersonalCenter',
      children: [
        {
          path: '',
          redirect: '/personal-center/account-management/'
        },
        {
          path: 'account-management/',
          component: AccountManagement,
          name: 'accountManagement',
          meta: {
            title: 'EulerTest'
          }
        },
        {
          path: 'account-info/',
          component: AccountInfo,
          name: 'accountInfo',
          meta: {
            title: 'EulerTest'
          }
        },
        {
          path: 'org-management/',
          component: OrgManagement,
          name: 'orgManagement',
          meta: {
            title: 'EulerTest'
          }
        },
        {
          path: 'authority-management/',
          component: authorityManagement,
          name: 'authorityManagement',
          children: [
            {
              path: 'rules-management/',
              component: rulesManagement,
              name: 'rulesManagement'
            },
            {
              path: 'roles-management/:roleId',
              component: rolesManagement,
              name: 'rolesManagement'
            }
          ],
          meta: {
            title: 'EulerTest'
          }
        },
        {
          path: 'users-management/',
          component: usersManagement,
          name: 'usersManagement',
          meta: {
            title: 'EulerTest'
          }
        },
        {
          path: 'config-management/',
          component: configManagement,
          name: 'configManagement',
          meta: {
            title: 'EulerTest'
          }
        },
        {
          path: 'security-setting/',
          component: securitySetting,
          name: 'securitySetting',
          meta: {
            title: 'EulerTest'
          }
        },
        {
          path: 'news/',
          component: News,
          name: 'news',
          meta: {
            title: 'EulerTest'
          }
        }
      ]
    },
    {
      path: '/:catchAll(.*)',
      component: NotFound,
      name: 'NotFound'
    }
  ]
});
export default router;
