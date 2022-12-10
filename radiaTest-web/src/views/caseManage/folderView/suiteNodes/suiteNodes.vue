<template>
  <div class="suiteNodes-container">
    <n-tabs type="line" animated>
      <n-tab-pane name="detail" tab="测试套详情">
        <collapse-list :list="detailList" />
      </n-tab-pane>
      <n-tab-pane name="document" tab="软件包/特性文档">
        <Document />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>
<script setup>
import { getSuiteItem } from '@/api/get';
import Document from './document.vue';
import collapseList from '@/components/collapseList/collapseList.vue';

const router = useRoute();

const detailList = ref([
  {
    title: '基础信息',
    name: 'baseInfo',
    rows: [
      {
        cols: [
          { label: '测试套名', value: '' },
          { label: '描述', value: '' },
        ],
      },
      {
        cols: [
          { label: '机器类型需求', value: '' },
          { label: '机器数量需求', value: '' },
        ],
      },
      {
        cols: [
          { label: '网卡需求', value: '' },
          { label: '磁盘需求', value: '' },
        ],
      },
    ],
  },
  {
    title: '所属代码仓信息',
    name: 'repoDetails',
    rows: [
      {
        cols: [
          { label: '代码仓名', value: '' },
          { label: '是否开启同步', value: '' },
        ],
      },
      {
        cols: [
          { label: '代码仓地址', value: '' },
        ],
      },
    ],
  },
  {
    title: '执行框架信息',
    name: 'frameworkDetails',
    rows: [
      {
        cols: [
          { label: '执行框架名', value: '' },
          { label: '是否已适配', value: '' },
        ],
      },
      {
        cols: [
          { label: '代码仓', value: '' },
          { label: '相对路径', value: '' },
        ],
      },
    ],
  },
]);

function dispatchRefreshEvent() {
  window.dispatchEvent(
    new CustomEvent('refreshEvent', {
      detail: {
        caseNodeId: window.atob(router.params.taskId)
      },
    })
  );
}

onMounted(() => {
  getSuiteItem(window.atob(router.params.suiteId))
    .then((res) => {
      detailList.value = [
        {
          title: '基础信息',
          name: 'baseInfo',
          rows: [
            {
              cols: [
                { label: '测试套名', value: res.data?.name },
                { label: '描述', value: res.data?.remark },
              ],
            },
            {
              cols: [
                { label: '机器类型需求', value: res.data?.machine_type },
                { label: '机器数量需求', value: res.data?.machine_num },
              ],
            },
            {
              cols: [
                { label: '网卡需求', value: res.data?.add_network_interface },
                { label: '磁盘需求', value: res.data?.add_disk },
              ],
            },
          ],
        },
        {
          title: '所属代码仓信息',
          name: 'repoDetails',
          rows: [
            {
              cols: [
                { label: '代码仓名', value: res.data?.git_repo?.name },
                { label: '是否开启同步', value: res.data?.git_repo?.sync_rule },
              ],
            },
            {
              cols: [
                { label: '代码仓地址', value: res.data?.git_repo?.git_url },
              ],
            },
          ],
        },
        {
          title: '执行框架信息',
          name: 'frameworkDetails',
          rows: [
            {
              cols: [
                { label: '执行框架名', value: res.data?.framework?.name },
                { label: '是否已适配', value: res.data?.framework?.adaptive },
              ],
            },
            {
              cols: [
                { label: '代码仓', value: res.data?.framework?.url },
                { label: '日志相对路径', value: res.data?.framework?.logs_path },
              ],
            },
          ],
        },
      ];
    });
  nextTick(() => {
    setTimeout(() => {
      if (Number(sessionStorage.getItem('refresh')) === 1) {
        dispatchRefreshEvent();
        sessionStorage.setItem('refresh', 0);
      }
    }, 500);
  });
});

onUnmounted(() => {
  detailList.value = [
    {
      title: '基础信息',
      name: 'baseInfo',
      rows: [
        {
          cols: [
            { label: '测试套名', value: '' },
            { label: '描述', value: '' },
          ],
        },
        {
          cols: [
            { label: '机器类型需求', value: '' },
            { label: '机器数量需求', value: '' },
          ],
        },
        {
          cols: [
            { label: '网卡需求', value: '' },
            { label: '磁盘需求', value: '' },
          ],
        },
      ],
    },
    {
      title: '所属代码仓信息',
      name: 'repoDetails',
      rows: [
        {
          cols: [
            { label: '代码仓名', value: '' },
            { label: '是否开启同步', value: '' },
          ],
        },
        {
          cols: [
            { label: '代码仓地址', value: '' },
          ],
        },
      ],
    },
    {
      title: '执行框架信息',
      name: 'frameworkDetails',
      rows: [
        {
          cols: [
            { label: '执行框架名', value: '' },
            { label: '是否已适配', value: '' },
          ],
        },
        {
          cols: [
            { label: '代码仓', value: '' },
            { label: '相对路径', value: '' },
          ],
        },
      ],
    },
  ];
});
</script>
<style lang="less" scoped>
.suiteNodes-container{
  height: 100%;
}
</style>
