<template>
  <div class="review-box">
    <div class="review-header">
      <div style="display:flex;width:60%">
        <n-select
          v-model:value="filter"
          :options="filterOptions"
          style="width:150px;margin-right: 10px;"
          @update:value="getData"
        />
        <n-input v-model:value="searchInfo" placeholder="搜索" style="width:100%" @change="getData">
          <template #suffix>
            <n-icon>
              <Search />
            </n-icon>
          </template>
        </n-input>
      </div>
      <n-button type="info" @click="showPendingModal">
        <template #icon>
          <Search />
        </template>
        查看未提交评审的修改
      </n-button>
    </div>
    <div class="review-tools">
      <n-button-group>
        <n-button text v-for="item in types" :key="item.value" @click="clickTypeBtn(item.value)">
          <div class="typeBtn">
            <div :class="['typeLabel', activeType === item.value ? 'active' : '']">{{ item.label }}</div>
            <n-badge class="typeCount" :value="item.count" :max="15" color="#f2f4f8" />
          </div>
        </n-button>
      </n-button-group>
    </div>
    <div class="review-body">
      <n-spin :show="loading" stroke="rgba(0, 47, 167, 1)">
        <caseReviewList
          :dataList="dataList"
          :page="page"
          :pageCount="pageCount"
          @change="pageChange"
          @update="getData"
        />
      </n-spin>
    </div>
    <modal-card
      :initX="300"
      title="未提交评审的修改"
      ref="pendingModal"
      confirmText="提交"
      @validate="pendingRef.submitCommit()"
      cancelText="关闭"
    >
      <template #form>
        <pendingReviewList
          :dataList="pendingData"
          :page="pendingPage"
          :pageCount="pendingPageCount"
          @change="pendingPageChange"
          ref="pendingRef"
          @update="
            () => {
              getPendingData();
              getData();
            }
          "
        />
      </template>
    </modal-card>
  </div>
</template>
<script>
import { modules } from './modules/index';
import { Search } from '@vicons/ionicons5';
import caseReviewList from '@/components/testcaseComponents/caseReviewList.vue';
import pendingReviewList from '@/components/testcaseComponents/pendingReviewList.vue';
import ModalCard from '@/components/CRUD/ModalCard.vue';
export default {
  components: {
    Search,
    caseReviewList,
    ModalCard,
    pendingReviewList
  },
  setup() {
    modules.getData();
    return {
      ...modules
    };
  }
};
</script>
<style lang="less" scoped>
.review-box {
  padding: 20px 40px;
  display: flex;
  flex-direction: column;

  .review-tools {
    flex-shrink: 0;
    background: #fcfcfc;
    color: #8c92a4;
    padding: 20px 10px;

    .typeBtn {
      margin: 0 20px;
      display: flex;
      align-items: center;

      .typeLabel {
        color: #8c92a4;
      }

      .active {
        color: #40485b;
        font-weight: bold;
        box-shadow: none;
      }

      .typeCount {
        margin-left: 5px;

        :deep(.n-base-slot-machine-current-number__inner) {
          color: #7687ab;
        }
      }
    }
  }

  .review-body {
    height: 100%;
    overflow-y: auto;
  }

  .review-header {
    display: flex;
    flex-shrink: 0;
    justify-content: space-between;
    margin: 10px 0;
  }
}
</style>
