<script setup>
import {useStore} from 'vuex';
import {ref} from 'vue';
import 'bytemd/dist/index.min.css';

const store = useStore();
const noticeList = store.state.notices.noticeList;
const catalogueList = ref([]);
const heading = ref([]);
const catalogue = res => {
  catalogueList.value = res;
};
const activeSelect = index => {
  heading.value[index]?.scrollIntoView();
};

const catalogueClass = (level) => {
  switch (level) {
    case 1:
      return 'item d1';
    case 2:
      return 'item d2';
    case 3:
      return 'item d3';
    case 4:
      return 'item d4';
    default:
      return 'item';
  }
};
</script>
<template>
  <n-layout has-sider>
    <n-layout-sider
        :width="275"
    >
      <div class="sider">
        <div v-for="item in noticeList" :key="item.id" class="hover">
          <n-badge color="green" dot style="padding: 0.5rem"/>
          <n-tag  bordered size="small" style="margin: 0.5rem" type="error">{{ item.tag }}</n-tag>
          <router-link :to="`/home/notice/${item.title}`">{{ item.title }}</router-link>
        </div>
      </div>
    </n-layout-sider>
    <n-layout-content id="notice" class="content" content-style="padding: 2rem;">
      <router-view @catalogue="catalogue"/>
    </n-layout-content>
    <n-layout-sider
        :width="275"
        content-style="padding-top: 0.5rem;"
    >
      <div>
        <n-anchor
            :bound="20"
            affix
            class="catalog-list"
            ignore-gap
            offset-target="#notice"
            :show-background="false"
            :show-rail="false"
        >
          <n-anchor-link v-for="(item, index) in catalogueList"
                         :key="index"
                         :class="catalogueClass(item.level)"
                         :href="`#heading-${index}`"
                         :title="item.text"
                         @click="activeSelect(index)"
          >
          </n-anchor-link>
        </n-anchor>
      </div>
    </n-layout-sider>
  </n-layout>
</template>

<style scoped>
a {
  color: black;
  text-decoration: none;
}

a:active {
  color: #3da8f5;
}

.router-link-active {
  text-decoration: none;
}

.content::-webkit-scrollbar {
  display: none;
}

.content {
  -ms-overflow-style: none; /* IE and Edge */
  scrollbar-width: none; /* Firefox */
}

.sider {
  padding: 0.5rem;
  margin-bottom: 0.5rem;
}

.hover:hover {
  background-color: rgb(238, 239, 241, 0.7);
}

.catalog-list .item.d1 {
  padding-left: 0.5rem;
//margin: 0;
}

.catalog-list .item.d2 {
  padding-left: 1.5rem;
}

.catalog-list .item.d3 {
  padding-left: 2.5rem;
}

.catalog-list .item.d4 {
  padding-left: 3.5rem;
}

.catalog-list .item {
  margin: 0;
  padding: 0;
//font-size: 1rem;
  font-weight: 400;
//line-height: 20px;
  text-rendering: optimizeLegibility;
}
</style>
