<template>
  <n-spin :show="showLoading" stroke="rgba(0, 47, 167, 1)">
    <div>
      <card-page title="消息中心">
        <n-tabs type="line" size="large" default-value="unreadNews">
          <n-tab-pane name="unreadNews">
            <template #tab>
              <n-badge :value="unreadPageInfo.total">
                <span>未读消息</span>
              </n-badge>
            </template>
            <n-list>
              <n-list-item v-for="(item, index) in unreadNewsList" :key="index" class="news">
                <p class="news-item" v-html="item.data.info"></p>
                <p class="news-date">
                  <span>{{ formatTime(item.create_time, 'yyyy-MM-dd hh:mm:ss') }}</span>
                </p>
                <div class="btnBox">
                  <n-space>
                    <n-button type="primary" @click="accept(item)" v-if="item.type === 1"> 接受 </n-button>
                    <n-button type="error" @click="refuse(item)" v-if="item.type === 1"> 拒绝 </n-button>
                    <n-button type="info" @click="read(index)" v-if="item.type === 0"> 已读 </n-button>
                  </n-space>
                </div>
              </n-list-item>
            </n-list>
            <div style="display: flex; justify-content: space-between">
              <n-button @click="readAll" type="primary">全部标记为已读</n-button>
              <n-pagination
                v-model:page="unreadPageInfo.page"
                :page-count="unreadPageInfo.pageCount"
                @update:page="unreadPageChange"
              />
            </div>
          </n-tab-pane>
          <n-tab-pane name="readNewsList" tab="已读消息">
            <n-list>
              <n-list-item v-for="(item, index) in readNewsList" :key="index" class="news">
                <p class="news-item" v-html="item.data.info"></p>
                <p class="news-date">
                  <span>{{ formatTime(item.create_time, 'yyyy-MM-dd hh:mm:ss') }}</span>
                </p>
                <div class="btnBox">
                  <n-space>
                    <n-button type="primary" @click="accept(item)" v-if="item.type === 1"> 接受 </n-button>
                    <n-button type="error" @click="refuse(item)" v-if="item.type === 1"> 拒绝 </n-button>
                  </n-space>
                </div>
              </n-list-item>
            </n-list>
            <div style="display: flex; justify-content: flex-end">
              <n-pagination
                v-model:page="readPageInfo.page"
                :page-count="readPageInfo.pageCount"
                @update:page="readPageChange"
              />
            </div>
          </n-tab-pane>
        </n-tabs>
      </card-page>
    </div>
  </n-spin>
</template>
<script>
import { modules } from './modules/index.js';

import cardPage from '@/components/common/cardPage';
import { formatTime } from '@/assets/utils/dateFormatUtils';

export default {
  components: {
    cardPage
  },
  setup() {
    modules.getUnreadNews();
    modules.getReadNews();
    document.addEventListener('reloadNews', () => {
      modules.getUnreadNews();
      modules.getReadNews();
    });
    return { formatTime, ...modules };
  }
};
</script>
<style lang="less" scope>
.news {
  position: relative;
  .btnBox {
    position: absolute;
    right: 50px;
    top: 50%;
    transform: translate(0, -50%);
  }
}
.news-item {
  font-size: 18px;
  color: rgba(0, 47, 167, 1);
}
.news-date {
  color: #ccc;
  font-size: 14px;
}
</style>
