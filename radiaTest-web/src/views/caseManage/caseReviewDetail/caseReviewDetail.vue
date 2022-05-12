<template>
  <div class="detail-container">
    <n-breadcrumb>
      <n-breadcrumb-item href="../casereview">
        用例评审
      </n-breadcrumb-item>
      <n-breadcrumb-item href="#">
        详情
      </n-breadcrumb-item>
    </n-breadcrumb>
    <div class="detail-content">
      <div class="left">
        <n-h3>
          {{ detailInfo.title }}
        </n-h3>
        <div style="display:flex;margin:20px 0;">
          <n-tag :type="statusTag[detailInfo.status]" style="margin-right:30px">
            {{ detailInfo.status }}
          </n-tag>
          {{ detailInfo.source }}
        </div>
        <div style="display:flex;justify-content:space-between;margin:20px 0;">
          <div>
            <userInfo :userInfo="detailInfo.creator">
            </userInfo>
            <span>
              创建于
              <span style="margin-left:15px">
                {{ formatTime(detailInfo.create_time, 'yyyy-MM-dd hh:mm:ss') }}
              </span>
            </span>
          </div>
          <div>
            <n-space>
              <n-button type="info" tag="a" href="#comment" text>评论</n-button>
              <n-button type="primary" :disabled="detailInfo.status!=='open'" text @click="handleModify('accepted')"
                >合入修改</n-button
              >
              <n-button type="error" :disabled="detailInfo.status!=='open'" text @click="handleModify('rejected')"
                >拒绝修改</n-button
              >
            </n-space>
          </div>
        </div>
        <n-tabs type="line">
          <n-tab-pane name="comment" tab="评论">
            <comment
              @update="getComment"
              v-for="(item, index) in comments"
              :key="index"
              :comment="item"
            />
            <div id="comment">
              <Editor v-model="commentInput" tag-name="div" :init="init" />
              <n-button type="primary" @click="commentCase">
                评论
              </n-button>
            </div>
          </n-tab-pane>
          <n-tab-pane name="case" tab="用例">
            <div v-if="oldContent.machine_type !== newContent.machine_type">
              机器类型：<span style="color:red">{{
                oldContent.machine_type
              }}</span>
              -> <span style="color:green">{{ newContent.machine_type }}</span>
            </div>
            <div v-if="oldContent.machine_num !== newContent.machine_num">
              机器数量：<span style="color:red">{{
                oldContent.machine_num
              }}</span>
              <span style="margin:0 10px">-></span>
               <span style="color:green">{{ newContent.machine_num }}</span>
            </div>
            <diff v-for="(item, index) in content" :key="index" :info="item" />
          </n-tab-pane>
        </n-tabs>
      </div>
      <div class="right">
        <!-- <div class="right-item">
          <div class="conent">审查</div>
          <div class="conent">未设置</div>
        </div>
        <div class="right-item">
          <div class="conent">优先级</div>
          <div class="conent">不指定</div>
        </div> -->
        <div class="right-item">
          <div class="conent">标签</div>
          <div class="conent">
            <n-tag :type="statusTag[detailInfo.status]">
              {{ detailInfo.status }}
            </n-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import comment from '@/components/testcaseComponents/comment.vue';
import { modules } from './modules';
import userInfo from '@/components/user/userInfo.vue';
import { formatTime } from '@/assets/utils/dateFormatUtils';
import Editor from '@tinymce/tinymce-vue';
import diff from '@/components/testcaseComponents/diff.vue';
export default {
  components: {
    comment,
    userInfo,
    Editor,
    diff,
  },
  setup() {
    modules.getDetail();
    modules.getComment();
    return {
      formatTime,
      ...modules,
    };
  },
};
</script>
<style lang="less" scoped>
#comment {
  margin-top: 20px;
}
.right {
  .right-item {
    display: flex;
    margin: 10px 0;
    .conent {
      flex: 1;
    }
  }
}
.detail-container {
  padding: 5px 15px;
  .detail-content {
    padding: 20px 0;
    display: flex;
    .left {
      flex: 7;
    }
    .right {
      flex: 3;
    }
  }
}
</style>
