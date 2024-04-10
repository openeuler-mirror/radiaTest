<template>
  <div class="comment-box">
    <div class="comment-title">
      <div>
        <userInfo :userInfo="comment.creator" />
        <div style="display: inline-block" v-if="isReply">
          <span style="margin: 0 20px">回复</span>
          <span>
            <userInfo :userInfo="comment.reply" />
          </span>
        </div>
        <span class="title-item">
          {{ formatTime(comment.create_time, 'yyyy-MM-dd hh:mm:ss') }}
        </span>
      </div>
      <n-button type="error" text @click="deleteComment"> 删除 </n-button>
    </div>
    <div v-dompurify-html="comment.content"></div>
    <div class="comment-action" v-show="!showComment">
      <n-button @click="reply" text>
        <template #icon>
          <n-icon><Chat /> </n-icon>
        </template>
        回复
      </n-button>
    </div>
    <div v-if="comment.child_list?.length" style="padding: 10px 20px; padding-right: 0">
      <comment
        style="border: none"
        v-for="(item, index) in comment.child_list"
        :comment="item"
        :isReply="true"
        :key="index"
      />
    </div>
    <div v-if="showComment">
      <editor v-model="commentInput" tag-name="div" :init="init" />
    </div>
    <n-space v-if="showComment">
      <n-button type="primary" @click="replay"> 回复 </n-button>
      <n-button type="info" @click="cancelReply"> 取消 </n-button>
    </n-space>
  </div>
</template>
<script>
import { Chat } from '@vicons/carbon';
import { init } from '@/views/taskManage/task/modules/taskDetail';
import Editor from '@tinymce/tinymce-vue';
import userInfo from '@/components/user/userInfo.vue';
import { createComment } from '@/api/post';
import { formatTime } from '@/assets/utils/dateFormatUtils';
import { deleteComment } from '@/api/delete';
import comment from '@/components/testcaseComponents/comment.vue';
import { getComment } from '@/views/caseManage/caseReviewDetail/modules/comment.js';
export default {
  name: 'comment',
  props: ['comment', 'isReply'],
  components: {
    Chat,
    Editor,
    userInfo,
    comment,
  },
  data() {
    return {
      showComment: false,
      init,
      commentInput: '',
    };
  },
  methods: {
    deleteComment() {
      deleteComment(this.comment.id).then(() => {
        getComment();
      });
    },
    formatTime(time, format) {
      return formatTime(time, format);
    },
    reply() {
      this.showComment = true;
    },
    replay() {
      createComment(this.comment.commit_id, {
        parent_id: this.comment.id,
        content: this.commentInput,
      }).then(() => {
        this.cancelReply();
        getComment();
      });
    },
    cancelReply() {
      this.showComment = false;
    },
  },
};
</script>
<style lang="less" scoped>
.comment-box {
  border-bottom: 1px solid #ccc;
}

.comment-title {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .title-item {
    margin: 0 10px;
  }
}
</style>
