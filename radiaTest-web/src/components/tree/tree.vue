<template>
  <n-tree
    block-line
    :data="data"
    :render-prefix="renderPrefix"
    :render-suffix="renderSuffix"
    :selectable="true"
    ref="tree"
    remote
    :on-load="handleLoad"
    @contextmenu="handleContextMenu"
    @update:selected-keys="selectMenu"
    :expanded-keys="expandKeys"
    @update:expanded-keys="expand"
    :selected-keys="selectKey"
  />
  <n-dropdown
    placement="bottom-start"
    @select="handleSelect"
    trigger="manual"
    :x="x"
    :y="y"
    :options="activeItem.actions"
    :show="showDropdown"
    :on-clickoutside="onClickoutside"
  />
</template>
<script>
import { h, ref } from 'vue';
import { NIcon } from 'naive-ui';

function renderPrefix({ option }) {
  const prefix = h(
    NIcon,
    { color: option.iconColor || '#0e7a0d' },
    {
      default: () => h(option.icon),
    }
  );
  return prefix;
}
export default {
  props: {
    data: {
      type: Object,
      required: true,
    },
    expandKeys: Array,
    selectKey: String
  },
  methods: {
    expand(str) {
      this.$emit('expand', str);
    },
    selectMenu(key, options) {
      this.$emit('menuClick', { key, options });
    },
    handleSelect(key, options) {
      const result = {
        action: options,
        contextmenu: this.activeItem,
      };
      this.showDropdown = false;
      this.$emit('selectAction', result);
    },
    handleLoad(node) {
      return new Promise((resolve, reject) => {
        this.$emit('load', node, (res) => {
          res === 'success' ? resolve() : reject(res);
        });
      });
    },
    getTreeNodeLevel(node) {
      return node.children[0].querySelectorAll('div.n-tree-node-indent').length;
    },
    getNodeIndex(node, index, result) {
      const level = this.getTreeNodeLevel(node);
      if (level !== 0) {
        let parentIndex;
        let parentNode;
        for (let i = index; i >= 0; i--) {
          if (
            this.getTreeNodeLevel(this.$refs.tree.$el.children[i]) ===
            level - 1
          ) {
            parentIndex = i;
            parentNode = this.$refs.tree.$el.children[i];
            let count = 0;
            for (let j = index - 1; j >= i; j--) {
              this.getTreeNodeLevel(this.$refs.tree.$el.children[j]) === level ? count++ : '';
            }
            result.unshift(count);
            break;
          }
        }
        this.getNodeIndex(parentNode, parentIndex, result);
      } else {
        let count = -1;
        for (let i = 0; i < this.$refs.tree.$el.children.length; i++) {
          if (this.getTreeNodeLevel(this.$refs.tree.$el.children[i]) === 0) {
            count++;
          }
          if (this.$refs.tree.$el.children[i] === node) {
            break;
          }
        }
        result.unshift(count);
      }
    },
    handleContextMenu(e) {
      e.preventDefault();
      const element = e.path.find((item) => {
        return item.classList.contains('n-tree-node-wrapper');
      });
      const index = Array.from(this.$refs.tree.$el.children).findIndex(
        (item) => {
          return item === element;
        }
      );
      const subscriptArr = [];
      this.getNodeIndex(element, index, subscriptArr);
      let temp = this.data;
      subscriptArr.forEach((item) => {
        if (Array.isArray(temp)) {
          temp = temp[item];
        } else {
          temp = temp.children[item];
        }
      });
      this.activeItem = temp;
      this.showDropdown = false;
      this.$nextTick(() => {
        this.showDropdown = true;
        this.x = e.clientX;
        this.y = e.clientY;
      });
    },
  },
  setup() {
    const tree = ref(null);
    const x = ref(0);
    const y = ref(0);
    const activeItem = ref({ actions: '' });
    const showDropdown = ref(false);
    return {
      x,
      y,
      tree,
      activeItem,
      showDropdown,
      renderPrefix,
      onClickoutside() {
        showDropdown.value = false;
      },
    };
  },
};
</script>
<style>
.n-tree .n-tree-node {
  word-break: break-all;
}
</style>
