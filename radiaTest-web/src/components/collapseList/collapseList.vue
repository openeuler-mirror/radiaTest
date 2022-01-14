<template>
  <div>
    <n-collapse :default-expanded-names="list.map((item) => item.name)">
      <n-collapse-item
        v-for="(item, index) in list"
        :key="index"
        :name="item[item.key || 'name']"
        :title="item.title"
      >
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
export default {
  props: {
    list: Array,
  },
};
</script>
<style lang="less" scoped>
.label {
  width: 80px;
  text-align: center;
}
</style>
