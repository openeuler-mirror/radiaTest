<template>
  <div>
    <n-collapse :default-expanded-names="list.map((item) => item.name)">
      <n-collapse-item
        v-for="(item, index) in list"
        :key="index"
        :name="item[item.key || 'name']"
        :title="item.title"
      >
        <div style="display:flex;justify-content:flex-end;margin:5px 0;">
          <n-icon
            v-if="item.editTools"
            v-show="!editRules[index].edit"
            @click="edit(index)"
            color="#2080F0"
            style="cursor:pointer"
          >
            <Edit />
          </n-icon>
          <n-space>
            <n-button
              @click="saveEdit(index)"
              text
              v-show="editRules[index].edit"
              type="primary"
            >
              保存
            </n-button>
            <n-button
              @click="cancelEdit(index)"
              text
              v-show="editRules[index].edit"
              type="info"
            >
              取消
            </n-button>
          </n-space>
        </div>
        <n-table :single-line="false" striped>
          <tbody>
            <tr v-for="(i, j) in item.rows" :key="j">
              <template v-for="(col, k) in i.cols" :key="k">
                <td class="label">{{ col.label }}</td>
                <td v-if="col.type === 'html'">
                  <a :href="col.value">{{ col.value }}</a>
                </td>
                <td v-else-if="col.type === 'pre'">
                  <pre>{{ col.value }}</pre>
                </td>
                <td v-else>{{ col.value }}</td>
              </template>
            </tr>
          </tbody>
        </n-table>
      </n-collapse-item>
    </n-collapse>
  </div>
</template>
<script>
import { Edit } from '@vicons/carbon';
import { ref } from 'vue';
export default {
  components: {
    Edit,
  },
  props: {
    list: Array,
  },
  methods: {
    edit(index) {
      this.$emit('edit', index);
    },
    saveEdit(index) {
      this.$emit('update', index);
    },
    cancelEdit() {
      this.$emit('cancel');
    },
  },
  setup(props) {
    const editRules = props.list.map((item) => {
      if (item.editTools) {
        return { useable: true, edit: false };
      }
      return { useable: false, edit: false };
    });
    return {
      editRules: ref(editRules),
    };
  },
};
</script>
<style lang="less" scoped>
.label {
  width: 80px;
  text-align: center;
}
.line {
  border: 1px solid #000;
}
</style>
