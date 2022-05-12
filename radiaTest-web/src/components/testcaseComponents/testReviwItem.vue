<template>
  <div class="item-container">
    <div class="item-title">
      <div>
        <n-button
          tag="a"
          type="info"
          @click="gotoDetail"
          text
          class="title"
          style="font-size:20px;font-weight:bold;margin-right:20px"
        >
          {{ info.title }}
        </n-button>
        <span style="margin:0 5px;" v-if="info.org_name">
          <n-icon>
            <Organization20Regular />
          </n-icon>
          {{ info.org_name }}
        </span>
        <span style="margin:0 5px" v-if="info.group_name">
          <n-icon>
            <GroupsOutlined />
          </n-icon>
          {{ info.group_name }}
        </span>
      </div>
      <n-dropdown :options="options" @select="selectAction">
        <n-button text>...</n-button>
      </n-dropdown>
    </div>
    <div class="item-content">
      {{ info.source }}
    </div>
    <div class="item-action">
      <div class="action-item">
        <div class="user item">
          <n-icon class="label">
            <User />
          </n-icon>
          <userInfo :userInfo="info.creator">
          </userInfo>
        </div>
        <div class="chat item">
          <n-icon class="label">
            <Chat />
          </n-icon>
          <span>{{ info.comment_count }}</span>
        </div>
        <div class="date item">
          创建于
          <span style="margin-left:10px">{{
            formatTime(info.create_time, 'yyyy-MM-dd hh:mm:ss')
          }}</span>
        </div>
      </div>
      <div class="action-item">
        <div class="item">
          <div style="display:flex;align-items:center">
            <span class="label">
              审查人:
            </span>
            <userInfo :userInfo="info.reviewer">
            </userInfo>
          </div>
        </div>
        <div class="item">
          <span style="margin-left:10px">{{
            formatTime(info.review_time, 'yyyy-MM-dd hh:mm:ss')
          }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
<script>
import {Organization20Regular,} from '@vicons/fluent';

import { User } from '@vicons/tabler';
import { Chat } from '@vicons/carbon';
import { GroupsOutlined } from '@vicons/material';
import { formatTime } from '@/assets/utils/dateFormatUtils';
import userInfo from '@/components/user/userInfo.vue';
export default {
  props: ['info','options'],
  components: {
    User,
    Chat,
    userInfo,
    GroupsOutlined,
    Organization20Regular,
  },
  methods: {
    selectAction(key){
      this.$emit('selectAction',{key,info:this.info});
    },
    gotoDetail() {
      this.$router.push({
        name: 'caseReviewDetail',
        params: { commitId: this.info.id },
      });
    },
    formatTime(value, str) {
      return formatTime(value, str);
    },
  },
  data() {
    return {
    };
  },
};
</script>
<style scoped lang="less">
.item-container {
  border-bottom: 1px solid #ccc;
  padding: 10px 20px;
  .item-title {
    .title {
      cursor: pointer;
    }
    .title:hover {
      color: #2080f0;
    }
    display: flex;
    justify-content: space-between;
  }
  .item-content {
    padding: 20px 0px;
    color:#ccc;
  }
  .item-action {
    display: flex;
    justify-content: space-between;
    .action-item {
      .item {
        margin: 0 10px;
        display: inline-block;
        .label {
          margin-right: 10px;
        }
      }
    }
  }
}
</style>
