<template>
  <template v-if="dataList?.length">
    <n-checkbox-group v-model:value="value">
      <n-space>
        <n-checkbox
          v-for="(item, index) in dataList"
          :key="index"
          :value="item.id"
        >
          <testReviewItem
            :key="index"
            :info="item"
            :options="options"
            @selectAction="handleAction"
          />
        </n-checkbox>
      </n-space>
    </n-checkbox-group>
  </template>
  <n-empty style="height:300px" description="暂无数据" v-else> </n-empty>
  <div style="padding:10px 0;display:flex;justify-content:center">
    <n-pagination
      :page="page"
      :page-count="pageCount"
      @update:page="pageChange"
    />
  </div>
  <caseModifyForm
    :formValue="formValue"
    ref="modifyModal"
    @submit="submitModify"
  />
</template>
<script>
import testReviewItem from '@/components/testcaseComponents/testReviwItem.vue';
import { renderIcon } from '@/assets/utils/icon';
import { BorderColorFilled } from '@vicons/material';
import { ArrowAltCircleUpRegular } from '@vicons/fa';
import {
  modifyCommitStatus,
  modifyCommitStatusBatch,
  modifyCommitInfo,
} from '@/api/put';
import caseModifyForm from '@/components/testcaseComponents/caseModifyForm.vue';
export default {
  components: {
    testReviewItem,
    caseModifyForm,
  },
  props: ['dataList', 'page', 'pageCount'],
  data() {
    return {
      value: [],
      formValue: {},
      options: [
        {
          label: '修改',
          key: 'modify',
          icon: renderIcon(BorderColorFilled, 'blue'),
        },
        {
          label: '提交',
          key: 'submit',
          icon: renderIcon(ArrowAltCircleUpRegular, 'rgba(0, 47, 167, 1)'),
        },
      ],
    };
  },
  methods: {
    filterField(obj, fields) {
      const result = {};
      for (const key of fields) {
        result[key] = obj[key];
      }
      return result;
    },
    submitModify(form) {
      modifyCommitInfo(this.formValue.id, {
        ...this.filterField(form, [
          'case_description',
          'description',
          'machine_num',
          'machine_type',
          'title',
          'steps',
          'expectation'
        ]),
        open_edit: true,
      }).then(()=>{
        this.$refs.modifyModal.close();
      });
    },
    handleAction({ info, key }) {
      if (key === 'submit') {
        modifyCommitStatus(info.id, { status: 'open' }).then(()=>{
          this.$emit('update');
        });
      } else if (key === 'modify') {
        this.formValue = info;
        this.$refs.modifyModal.show();
      }
    },
    submitCommit() {
      console.log(this.value);
      modifyCommitStatusBatch({ commit_ids: this.value }).then(()=>{
        this.$emit('update');
      });
    },
    pageChange(page) {
      this.$emit('change', page);
    },
  },
};
</script>
