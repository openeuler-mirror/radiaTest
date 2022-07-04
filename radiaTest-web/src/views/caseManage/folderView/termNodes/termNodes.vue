<template>
  <div class="termNodes-container">
    <div class="leftPart">
      <div class="part1">
        <div class="count">
          <div class="txt">用例统计</div>
          <div class="num">{{ itemsCount }}</div>
        </div>
        <div class="chart" id="termAutomationRate-pie"></div>
      </div>
      <div class="part2">
        <div class="title">自动化脚本代码仓</div>
        <div class="search">
          <n-button type="primary" round @click="showRepoModal"> 注册代码仓 </n-button>
          <n-icon size="20" color="#666666" class="refreshIcon" @click="getCodeData"> <md-refresh /> </n-icon>
          <n-input type="text" size="small" v-model:value="keyword">
            <template #prefix>
              <n-icon color="666666" :component="Search" />
            </template>
          </n-input>
        </div>
        <div class="table">
          <n-data-table
            :pagination="codePagination"
            :columns="codeColumns"
            :data="codeData"
            :row-key="(row) => row.id"
            :loading = "codeTableLoading"
            remote
          />
        </div>
      </div>
    </div>
    <div class="rightPart">
      <div class="part1">
        <div class="count count1">
          <div class="txt">月commit合入</div>
          <div class="num">{{ commitMonthCount }}</div>
        </div>
        <div class="count count1">
          <div class="txt">周commit合入</div>
          <div class="num">{{ commitWeekCount }}</div>
        </div>
        <div class="chart">
          <n-select v-model:value="commitSelectedTime" :options="timeOptions" />
          <div id="termCommitCounts-line"></div>
        </div>
      </div>
      <div class="part2">
        <div class="part2-left">
          <div class="title">基线管理</div>
          <n-input type="text" size="small" v-model:value="baselineKeyword">
            <template #prefix>
              <n-icon color="666666" :component="Search" />
            </template>
          </n-input>
        </div>
        <div class="part2-right">
          <div class="top">
            <div class="txts">
              <n-icon size="16" color="#666666">
                <Cubes />
              </n-icon>
              树状视图
            </div>
            <div>
              <n-button type="primary">
                继承
              </n-button>
              <n-button type="error">
                清空
              </n-button>
            </div> 
          </div>
          <vue-kityminder
            ref="termNodeKityminder"
            theme="fresh-blue"
            template="right"
            :value="val"
            :toolbar-status="toolbar"
          >
          </vue-kityminder>
        </div>
      </div>
    </div>
    <n-modal
      v-model:show="repoModal"
      preset="dialog"
      title="注册代码仓"
    >
      <n-form
        ref="repoRef1"
        label-placement="top"
        :model="repoForm"
        :rules="repoRules"
      >
        <n-form-item label="所属框架" path="framework_id">
          <n-select
            v-model:value="repoForm.framework_id"
            placeholder="请选择"
            :options="frameworkList"
          />
        </n-form-item>
        <n-form-item label="名称" path="name">
          <n-input
            v-model:value="repoForm.name"
            placeholder="请输入名称"
          />
        </n-form-item>
        <n-form-item label="代码仓地址" path="git_url">
          <n-input v-model:value="repoForm.git_url" placeholder="仓库地址" />
        </n-form-item>
        <n-form-item label="是否允许同步" path="sync_rule">
          <n-switch v-model:value="repoForm.sync_rule">
            <template #checked> 是 </template>
            <template #unchecked> 否 </template>
          </n-switch>
        </n-form-item>
        <n-form-item label="是否已适配" path="is_adapt">
          <n-switch v-model:value="repoForm.is_adapt">
            <template #checked> 是 </template>
            <template #unchecked> 否 </template>
          </n-switch>
        </n-form-item>
      </n-form>
      <template #action>
        <n-space style="width: 100%">
          <n-button type="error" ghost size="large" @click="closeRepoForm">
            取消
          </n-button>
          <n-button size="large" @click="submitRepoForm" type="primary" ghost>
            提交
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>
<script>
import { modules } from './modules/index';
import { ref, onMounted } from 'vue';
import { MdRefresh } from '@vicons/ionicons4';
import { Search } from '@vicons/ionicons5';
import { Cubes } from '@vicons/fa';
export default {
  components: { MdRefresh, Cubes },
  setup() {
    onMounted(() => {
      modules.initData();
      modules.getCodeData();
    });
    return {
      Search,
      commitSelectedTime: ref('week'),
      timeOptions: [
        { label: '近一周', value: 'week' },
        { label: '近半月', value: 'halfMonth' },
        { label: '近一月', value: 'month' },
      ],
      baselineKeyword: ref(''),
      val: {
        data: {
          id: 1,
          text: 'test'
        },
        children: [
          { data: { id: 1-2, text: 'test1'},
            children:[
              {data:{id: 1-2-1,text:'1-2-1'}}
            ]
          },
          {data: { id: 1-3,text: 'test3'}},
          {data: { id: 1-4,text: 'test4'}},
          {data: { id: 1-5,text: 'test5'}},
        ]
      },
      toolbar: {
        appendSiblingNode: true,
        arrangeUp: false,
        arrangeDown: false,
        text: true,
        template: false,
        theme:false,
        hand: false,
        resetLayout: false,
        zoomIn: false,
        zoomOut:false
      },
      ...modules
    };
  }
};
</script>
<style lang="less" scoped>
.termNodes-container{
  display: flex;
  justify-content: space-between;
  flex-wrap: nowrap;
  .leftPart{
    width:30%;
    height: 100%;
    .part1{
      .chart{
        height: 100%;
        width: 50%;
      }
      .count{
        width: 50%;
      }
    }
    .part2{
      padding:20px;
      border:1px solid #eee;
      border-radius: 4px;
      margin-top:20px;
      .title{
        color: #000000;
        font-size: 16px;
        margin-bottom: 10px;
      }
      .search{
        overflow: hidden;
        margin-bottom: 15px;
        .n-button{
          float: left;
        }
        .n-input{
          float: right;
          width:200px;
          margin-right: 10px;
          margin-top:3px;
        }
        .n-icon.refreshIcon{
          float: right;
          margin-top:6px;
          cursor: pointer;
        }
      }
    }
    
  }
  .rightPart{
    width:calc(70% - 20px);
    height: 100%;
    .part1{
      .chart{
        height: 100%;
        width: 60%;
        .n-select{
          float: right;
          width: 20%;
          z-index: 1;
          margin-right: 20px;
        }
        #termCommitCounts-line{
          height: 100%;
        }
      }
      .count{
        width: 20%;
      }
    }
    .part2{
      display: flex;
      border:1px solid #eee;
      border-radius: 4px;
      margin-top:20px;
      justify-content: space-between;
      min-height: 600px;
      .part2-left{
        width:20%;
        padding:20px;
        border-right: 1px solid #eee;
        .title{
          font-size: 16px;
          color:#000000;
        }
        .n-input{
          margin:10px 0;
        }
      }
      .part2-right{
        width:80%;
        .top{
          height: 56px;
          width: calc(100% - 40px);
          display: flex;
          justify-content: space-between;
          align-items: center;
          color: #000000;
          font-size: 14px;
          border-bottom: 1px solid #eee;
          padding-left: 20px;
          padding-right: 20px;
          .txts{
            display: flex;
            align-items: center;
            color:#666666;
            i{
              margin-right: 5px;
            }
          }
          .n-button{
            margin-left: 20px;
            height: 30px;
            padding-left: 24px;
            padding-right: 24px;
            border-radius: 24px;
          }
        }
      }
    }
  }
  .part1{
    height: 200px;
    border:1px solid #eee;
    padding-top: 20px;
    padding-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-radius: 4px;
    .count{
      text-align: center;
      height: auto;
      .txt{
        font-size: 14px;
        margin-bottom: 15px;
      }
      .num{
        font-family: Arial, Helvetica, sans-serif;
        font-size: 32px;
      }
    }
  }
}
</style>
<style lang="less">
.termNodes-container{
  .vue-kityminder{
    width: 100%;
    height: 100%;
    .vue-kityminder-toolbar-left{
      margin-top:20px;
      margin-left:20px;
      top:0 !important;
      left:0 !important;
      .vue-kityminder-btn{
        padding:8px 12px;
        font-size:14px;
      }
      .vue-kityminder-ml{
        margin-left:8px;
      }
      .vue-kityminder-control{
        padding: 8px;
      }
    }
  }
}
</style>
