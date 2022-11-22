<template>
  <div class="document-container">
    <div class="leftPart">
      <div 
        v-for="(txt, txtIndex) in documentList" 
        :key="txtIndex" 
        :class="[{active: checkedItem === txt.id}, 'item']"
        @click="handleClick(txt)"
      >
        <n-icon color="666666" size="20" :component="Document" />
        <span> {{ txt.title }} </span>
      </div>
    </div>
    <div class="rightPart">
      <iframe
        :src="iframeUrl"
        frameborder="0"
        width="100%"
        height="100%"
      ></iframe>
    </div>
  </div>
</template>
<script>
import { modules } from './modules/index';
import { onMounted, ref } from 'vue';
import { Document } from '@vicons/carbon';
export default {
  components: { },
  setup() {
    onMounted(() => {
      modules.documentInit();
    });
    return {
      Document,
      documentList: modules.documentList,
      checkedItem: ref(''),
      iframeUrl: ref('')
    };
  },
  methods: {
    handleClick(txt) {
      this.checkedItem = txt.id;
      this.iframeUrl = txt.iframeUrl;
    }

  }
};
</script>
<style lang="less" scoped>
.document-container{
  display: flex;
  justify-content: flex-start;
  .leftPart{
    width:20%;
    padding: 10px 10px 10px 0;
    border-right: 1px solid #eee;
    .item{
      padding: 0 8px;
      height: 40px;
      display: flex;
      align-items: center;
      font-size: 12px;
      color:#000;
      cursor: pointer;
      border-radius: 5px;
      margin-bottom: 10px;
      &:hover,
      &.active{
        background-color: #d2daf5;
      }
      .n-icon{
        color: #666666;
        margin-right: 5px;
      }
      span{
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

    }
  }
}

</style>
<style lang="less">
.document-container{
  
}
</style>

