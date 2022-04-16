<template>
  <li class="timeline-item">
    <div style="display: flex">
      <div :style="{ width: leftWidth + 'px', flexShrink: 0 }">
        <div class="item-tail"></div>
        <div
          class="item-node"
          :class="[type !== 'image' ? `item-node-${type}` : '']"
          :style="{height:nodeHeght||'',width:nodeWidth||''}"
        >
          <slot name="node"> </slot>
        </div>
        <div class="item-wrapper">
          <div class="item-content">{{ title }}</div>
          <div class="item-process">{{ process }}</div>
          <n-space class="item-result" justify="space-between" align="center">
            {{ content }}
            <n-tag v-if="tag !== ''" size="small" :type="tagType">{{ tag }}</n-tag>
          </n-space>
          <div class="item-time" ref="time">{{ timestamp }}</div>
        </div>
      </div>
      <div>
        <slot></slot>
      </div>
    </div>
  </li>
</template>
<script>
export default {
  props: {
    type: {
      type: String,
      default: 'info',
    },
    leftWidth: {
      type: Number,
      default: 200,
    },
    title: String,
    timestamp: String,
    process: String,
    content: String,
    tag: String,
    tagType:String,
    nodeHeght:String,
    nodeWidth:String
  },
};
</script>
<style scoped lang="less">
.timeline-item {
  position: relative;
  padding-bottom: 20px;
  .item-tail {
    position: absolute;
    left: 4px;
    height: 100%;
    border-left: 2px solid #e4e7ed;
  }
  .item-node {
    left: -2px;
    width: 10px;
    height: 10px;
    position: absolute;
    background-color: #fff;
    border: 2px solid #ccc;
    border-radius: 50%;
    display: flex;
    justify-content: center;
    align-items: center;
  }
  .item-node-error {
    border: 2px solid #d03050 !important;
  }
  .item-node-success {
    border: 2px solid #36ad6a !important;
  }
  .item-node-primary {
    border: 2px solid rgba(0, 47, 167, 1) !important;
  }
  .item-node-warning {
    border: 2px solid #f0a020 !important;
  }
  .item-wrapper {
    position: relative;
    padding-left: 28px;
    top: -3px;
    .item-content {
      overflow: hidden;
      color: #6395f8;
      text-overflow: ellipsis;
      word-break: break-word;
    }
    .item-time {
      margin-top: 8px;
      color: #909399;
      line-height: 1;
      font-size: 13px;
    }
    .item-process {
      margin-top: 8px;
    }
    .item-result {
      margin-top: 8px;
    }
  }
}
</style>
