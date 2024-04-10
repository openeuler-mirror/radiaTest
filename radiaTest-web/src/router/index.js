import { createRouter, createWebHistory } from 'vue-router';
import Home from '@/views/home/Home';
import Dashboard from '@/views/dashboard/Dashboard';
import Testcase from '@/views/caseManage/testcase/Testcase';
import Report from '@/views/taskManage/report/Report.vue';
import Task from '@/views/taskManage/task/Task';
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
import newLogin from '@/views/login/newLogin.vue';
import frameWork from '@/views/caseManage/frameWork/frameWork.vue';
import Blank from '@/views/resultPage/Blank.vue';



const routerHistory = createWebHistory();
const router = createRouter({
  history: routerHistory,
  routes: [
    {
      path: '/',
      redirect: '/home/version-management'
    },

    {
      path: '/home/',
      redirect: { name: 'task' },
      component: Home,
      name: 'home',
      meta: {
        title: 'raidaTest测试平台'
      },
      children: [
        {
          path: 'workbench/',
          component: Dashboard,
          redirect: { name: 'task' },
          meta: {
            title: 'raidaTest测试平台'
          },
          children: [
            {
              path: 'task/',
              component: Task,
              name: 'task'
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
            },

          ]
        },
        {
          path: 'version-management/',
          redirect: { name: 'vmProduct' },
          component: versionManagement,
          children: [
            {
              path: 'product/',
              component: Product,
              name: 'vmProduct',
              meta: {
                title: '产品版本管理'
              }
            },
            {
              path: 'milestone/',
              component: Milestone,
              name: 'vmMilestone',
              meta: {
                title: '里程碑管理'
              }
            }
          ]
        },

        {
          path: 'tcm/',
          redirect: { name: 'folderview' },
          component: CaseManagement,
          meta: {
            title: '用例管理'
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
            },
            {
              path: 'framework',
              component: frameWork,
              name: 'frameWork'
            }
          ]
        }
      ]
    },

    {
      path: '/login/',
      component: newLogin,
      name: 'login',
      meta: {
        title: '登录'
      }
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
      path: '/blank',
      component: Blank,
      name: 'blank'
    },
    {
      path: '/:catchAll(.*)',
      component: NotFound,
      name: 'NotFound'
    }
  ]
});
export default router;
