<template>
  <n-popover :disabled="disabled || data?.length === 0" trigger="click">
    <template #trigger>
      <div
        class="info"
        :style="{
          width: textWidth ? textWidth : '100%',
          color: data?.length ? '' : 'grey'
        }"
      >
        {{ data?.length ? text : '没有可用机器' }}
      </div>
    </template>
    <n-data-table
      :data="data"
      :columns="columns"
      :row-key="(row) => row.id"
      :checked-row-keys="checkedMachine"
      @update:checked-row-keys="handleCheck"
      :pagination="pagination"
    />
  </n-popover>
</template>
<script>
import { ColumnDefault } from '@/views/pmachine/modules/pmachineTableColumns';
import { ColumnDefault as vmColumns } from '@/views/vmachine/modules/vmachineTableColumns';
export default {
  props: ['data', 'text', 'checkedMachine', 'disabled', 'machineType', 'textWidth'],
  methods: {
    handleCheck(value) {
      this.$emit('checked', value);
    }
  },
  setup(props) {
    const columns = [
      {
        type: 'selection'
      },
      ...ColumnDefault
    ].map((item) => {
      if (item.type) {
        return item;
      }
      return { key: item.key, title: item.title };
    });
    const vmcols = JSON.parse(JSON.stringify(vmColumns)).splice(0, vmColumns.length - 1);
    const vmcol = [
      {
        type: 'selection'
      },
      ...vmcols
    ];
    return {
      columns: props.machineType === 'pm' ? columns : vmcol,
      pagination: {
        pageSize: 5
      }
    };
  }
};
</script>
<style scoped>
.info {
  color: #2080f0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
