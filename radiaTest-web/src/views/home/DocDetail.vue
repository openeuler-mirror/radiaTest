<template>
  <div>
    <Viewer id="markdown-body" class="markdown-body" :plugins="plugins" :key="route.params.title" :value="content"/>
  </div>
</template>
<script setup>
import { Viewer } from '@bytemd/vue-next';
import { getProcessor } from 'bytemd';
import 'bytemd/dist/index.min.css';
import { computed, ref, watchEffect } from 'vue';
import { useRoute } from 'vue-router';
import { visit } from 'unist-util-visit';
import 'katex/dist/katex.css';
import 'juejin-markdown-themes/dist/github.min.css';
import breaks from '@bytemd/plugin-breaks';
import gemoji from '@bytemd/plugin-gemoji';
import gfm from '@bytemd/plugin-gfm';
import highlight from '@bytemd/plugin-highlight';
import math from '@bytemd/plugin-math';
import mermaid from '@bytemd/plugin-mermaid';
import frontmatter from '@bytemd/plugin-frontmatter';
import mathLocal from '@bytemd/plugin-math/locales/zh_Hans.json';

const emit = defineEmits(['catalogue']);
const plugins = [breaks()
  , frontmatter()
  , gemoji()
  , gfm()
  , highlight()
  , math({
    locale: mathLocal,
    katexOptions: { output: 'html' }, // https://github.com/KaTeX/KaTeX/issues/2796
  })
  , mermaid()
];
const route = useRoute();
const content = ref(null);
const catalogueList = ref([]); // 目录
const currentName = computed(() => {
  return route.params.title;
});
const transformToId = () => {
  const articleDom = document.getElementById('markdown-body');
  if (articleDom?.children) {
    const children = Array.from(articleDom.children);
    if (children.length > 0) {
      let index = 0;
      for (let i = 0; i < children.length; i++) {
        const tagName = children[i].tagName;
        if (tagName === 'H1' || tagName === 'H2' || tagName === 'H3' || tagName === 'H4') {
          children[i].setAttribute('data-id', `heading-${index}`);
          children[i].setAttribute('id', `heading-${index}`);
          index++;
        }
      }
    }
  }
};
const stringifyHeading = (e) => {
  let result = '';
  visit(e, (node) => {
    if (node.type === 'text') {
      result += node.value;
    }
  });
  return result;
};
const process = () => {
  getProcessor({
    plugins: [
      {
        rehype: p =>
            p.use(() => (tree) => {
              if (tree && tree.children.length) {
                const items = [];
                tree.children
                    .filter(v => v.type === 'element')
                    .forEach((node) => {
                      // 过滤掉主题和高亮
                      // eslint-disable-next-line max-nested-callbacks
                      const removeTheme = node.children.filter(item => item.value?.includes('theme'));
                      // eslint-disable-next-line max-nested-callbacks
                      const removeHl = node.children.filter(item => item.value?.includes('highlight'));
                      if (node.tagName[0] === 'h'
                          && !!node.children.length
                          && removeTheme.length === 0
                          && removeHl.length === 0
                      ) {
                        const i = Number(node.tagName[1]);
                        items.push({
                          level: i,
                          text: stringifyHeading(node),
                        });
                      }
                    });
                catalogueList.value = items.filter(v => v.level === 1 || v.level === 2 || v.level === 3 || v.level === 4);
              }
            }),
      },
    ],
  }).processSync(content.value);
};
watchEffect(async () => {
  if (route.path.startsWith('/home/doc/')) {
    await import(`../../../../doc/${currentName.value}.md`)
        .then(e => {
          content.value = e.default;
          process();
          transformToId();
          emit('catalogue', catalogueList.value);
        });
  }
});
</script>
