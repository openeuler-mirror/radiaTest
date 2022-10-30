import { createRouter, createWebHistory } from 'vue-router';
import Home from '@/views/home/Home';
import Dashboard from '@/views/dashboard/Dashboard';
import Pmachine from '@/views/pmachine/Pmachine';
import Vmachine from '@/views/vmachine/Vmachine';
import Template from '@/views/testCenter/template/Template';
import TestCenterManagement from '@/views/testCenter/TestCenterManagement.vue';
import Job from '@/views/testCenter/job/Job';
import Testcase from '@/views/caseManage/testcase/Testcase';
import Blank from '@/components/public/Blank';
import Report from '@/views/taskManage/report/Report.vue';
import Task from '@/views/taskManage/task/Task';
import Require from '@/views/taskManage/require/Require.vue';
import PersonalBoard from '@/views/taskManage/personalBoard/PersonalBoard';
import strategyCenter from '@/views/strategyCenter/strategyCenter';
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
import configManagement from '@/views/personalCenter/configManagement.vue';
import securitySetting from '@/views/personalCenter/securitySetting.vue';
import caseReview from '@/views/caseManage/caseReview/caseReview.vue';
import caseReviewDetail from '@/views/caseManage/caseReviewDetail/caseReviewDetail.vue';
import resourcePool from '@/views/resourcePool/resourcePool.vue';
import versionManagement from '@/views/versionManagement/versionManagement.vue';
import Product from '@/views/versionManagement/product/product.vue';
import Milestone from '@/views/versionManagement/milestone/milestone.vue';
import NotFound from '@/views/resultPage/NotFound.vue';

const routerHistory = createWebHistory();
const router = createRouter({
  history: routerHistory,
  routes: [
    {
      path: '/',
      redirect: '/login'
    },
    {
      path: '/home/',
      redirect: '/home/workflow',
      component: Home,
      name: 'home',
      meta: {
        title: 'raidaTest测试平台'
      },
      children: [
        {
          path: 'workflow/',
          component: Dashboard,
          redirect: '/home/workflow/dashboard',
          meta: {
            title: 'raidaTest测试平台'
          },
          children: [
            {
              path: 'dashboard/',
              component: PersonalBoard,
              name: 'dashboard',
            },
            {
              path: 'task/',
              component: Task,
              name: 'task',
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
              path: 'distribution/',
              component: Distribution,
              name: 'distribution'
            },
            {
              path: 'design/',
              component: strategyCenter,
              name: 'design',
            },
            {
              path: 'testing/',
              redirect: '/home/workflow/testing/jobs',
              component: TestCenterManagement,
              children: [
                {
                  path: 'jobs/',
                  component: Job,
                  meta: {
                    title: '测试看板'
                  }
                },
                {
                  path: 'template/',
                  component: Template,
                  meta: {
                    title: '模板仓库'
                  }
                }
              ]
            },
          ]
        },
        {
          path: 'version-management/',
          redirect: '/home/version-management/product',
          component: versionManagement,
          children: [
            {
              path: 'product/',
              component: Product,
              meta: {
                title: '产品版本管理'
              }
            },
            {
              path: 'milestone/',
              component: Milestone,
              meta: {
                title: '里程碑管理'
              }
            }
          ]
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
                  name: 'pmachine'
                },
                {
                  path: 'vmachine/:machineId',
                  component: Vmachine,
                  name: 'vmachine'
                }
              ],
              meta: {
                title: '资源池管理'
              }
            },
            {
              path: 'pmachine/',
              component: Pmachine,
              meta: {
                title: '物理机资源池'
              }
            },
            {
              path: 'vmachine/',
              component: Vmachine,
              meta: {
                title: '虚拟机资源池'
              }
            }
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
              path: 'case-review/',
              component: caseReview,
              name: 'caseReview'
            },
            {
              path: 'case-review-detail/:commitId',
              component: caseReviewDetail,
              name: 'caseReviewDetail'
            },
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
                  path: 'node-detail/:taskid/',
                  component: taskDetails,
                  name: 'taskDetails'
                },
                {
                  path: 'org-node',
                  component: orgNode,
                  name: 'orgNode'
                },
                {
                  path: 'term-node',
                  component: termNode,
                  name: 'termNode'
                }
              ]
            },
            {
              path: 'framework',
              component: frameWork,
              name: 'frameWork'
            }
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
            title: '账号管理'
          }
        },
        {
          path: 'account-info/',
          component: AccountInfo,
          name: 'accountInfo',
          meta: {
            title: '基本信息'
          }
        },
        {
          path: 'org-management/',
          component: OrgManagement,
          name: 'orgManagement',
          meta: {
            title: '组织管理'
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
            title: '权限管理'
          }
        },
        {
          path: 'users-management/',
          component: usersManagement,
          name: 'usersManagement',
          meta: {
            title: '成员管理'
          }
        },
        {
          path: 'config-management/',
          component: configManagement,
          name: 'configManagement',
          meta: {
            title: '配置管理'
          }
        },
        {
          path: 'security-setting/',
          component: securitySetting,
          name: 'securitySetting',
          meta: {
            title: '安全设置'
          }
        },
        {
          path: 'news/',
          component: News,
          name: 'news',
          meta: {
            title: '消息中心'
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
