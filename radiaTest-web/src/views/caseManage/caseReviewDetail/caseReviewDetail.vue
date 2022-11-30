<template>
  <div class="detail-container">
    <n-breadcrumb>
      <n-breadcrumb-item @click="clickBreadCrumb">
        用例评审
      </n-breadcrumb-item>
      <n-breadcrumb-item href="#">
        详情
      </n-breadcrumb-item>
    </n-breadcrumb>
    <div class="detail-content">
      <div class="left">
        <n-h1>
          {{ detailInfo.title }}
        </n-h1>
        <div class="sourceWrap">
          <n-tag :type="statusTag[detailInfo.status]" style="margin-right:30px">
            {{ detailInfo.status }}
          </n-tag>
          {{ detailInfo.source }}
        </div>
        <div class="operateLineWrap">
          <div>
            <userInfo :userInfo="detailInfo.creator"> </userInfo>
            <span>
              创建于
              <span style="margin-left:15px">
                {{ formatTime(detailInfo.create_time, 'yyyy-MM-dd hh:mm:ss') }}
              </span>
            </span>
          </div>
          <div>
            <n-space>
              <n-button type="primary" v-if="detailInfo.status === 'open'" @click="handleModify('accepted')"
                >合入修改</n-button
              >
              <n-button type="error" v-if="detailInfo.status === 'open'" @click="handleModify('rejected')"
                >拒绝修改</n-button
              >
            </n-space>
          </div>
        </div>
        <n-tabs animated type="line">
          <n-tab-pane name="comment" tab="评论">
            <comment @update="getComment" v-for="(item, index) in comments" :key="index" :comment="item" />
            <div id="comment">
              <editor v-model="commentInput" tag-name="div" :init="init" />
              <n-button type="primary" @click="commentCase">
                评论
              </n-button>
            </div>
          </n-tab-pane>
          <n-tab-pane name="case" tab="用例">
            <div v-if="oldContent.machine_type !== newContent.machine_type">
              机器类型：<span style="color:red">{{ oldContent.machine_type }}</span> ->
              <span style="color:green">{{ newContent.machine_type }}</span>
            </div>
            <div v-if="oldContent.machine_num !== newContent.machine_num">
              机器数量：<span style="color:red">{{ oldContent.machine_num }}</span>
              <span style="margin:0 10px">-></span>
              <span style="color:green">{{ newContent.machine_num }}</span>
            </div>
            <diff v-for="(item, index) in content" :key="index" :info="item" />
          </n-tab-pane>
        </n-tabs>
      </div>
      <div class="right">
        <div class="right-item">
          <div class="title">审查</div>
          <div class="secondTitle">审查人员</div>
          <div class="item">
            <SelectBox
              :selectArray="tempArray"
              :multiple="true"
              :defaultValue="defaultChecker"
              :disabled="!editChecker"
              @updateValue="setChecker"
            ></SelectBox>
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
import { useRouter } from 'vue-router';
import { ref } from 'vue';
import SelectBox from '@/components/common/SelectBox.vue';

export default {
  components: {
    comment,
    userInfo,
    editor: Editor,
    diff,
    SelectBox
  },
  setup() {
    modules.getDetail();
    modules.getComment();
    modules.tinymce.init;
    const router = useRouter();
    const editChecker = ref(false);

    const tempArray = ref([
      {
        label: '测试1',
        value: 'test1'
      },
      {
        label: '测试2',
        value: 'test2'
      },
      {
        label: '测试3',
        value: 'test3'
      }
    ]);

    const defaultChecker = ref(['未设置']);

    const setChecker = (value) => {
      console.log(value);
    };

    const clickBreadCrumb = () => {
      router.push('/home/tcm/case-review');
    };

    return {
      formatTime,
      ...modules,
      clickBreadCrumb,
      editChecker,
      tempArray,
      setChecker,
      defaultChecker
    };
  }
};
</script>
<style lang="less" scoped>
#comment {
  margin-top: 20px;
}

.detail-container {
  padding: 20px 40px;

  .detail-content {
    padding: 20px 0;
    display: flex;

    .left {
      flex: 7;

      .sourceWrap {
        display: flex;
        margin: 20px 0;
        align-items: center;
      }

      .operateLineWrap {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 20px 0;
      }
    }

    .right {
      flex: 3;
      margin-left: 40px;
      padding: 30px;

      .title {
        margin-bottom: 10px;
        width: 100%;
        font-weight: 600;
        line-height: 28px;
      }

      .secondTitle {
        color: #8c92a4 !important;
        font-size: 12px;
        margin-bottom: 10px;
        width: 100%;
        font-weight: 600;
        line-height: 28px;
      }

      .item {
        color: rgba(191, 191, 191, 0.87);
      }
    }
  }
}
</style>
