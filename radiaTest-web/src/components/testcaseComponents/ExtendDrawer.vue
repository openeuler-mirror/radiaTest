<template>
  <n-drawer v-model:show="active" :width="1000" placement="right">
    <n-drawer-content>
      <template #header>
        <p style="width: 900px; text-align: center; margin: 0">
          <n-button
            @click="
              () => {
                active = false;
              }
            "
            size="medium"
            style="float: left;"
            quaternary
            circle
          >
            <n-icon :size="26">
              <arrow-left />
            </n-icon>
          </n-button>
          <span style="line-height: 34px; font-size: 28px">
            {{ rowData.name }}
          </span>
        </p>
      </template>
      <div>
        <testcase-content :form="formValue" @update="getData()" />
      </div>
    </n-drawer-content>
  </n-drawer>
</template>

<script>
import { ref, watch, defineComponent } from 'vue';

import { ArrowLeft32Filled as ArrowLeft } from '@vicons/fluent';
import TestcaseContent from './TestcaseContent.vue';

import testcaseTable from '@/views/caseManage/testcase/modules/testcaseTable.js';
import { getCaseDetail } from '@/api/get';
export default defineComponent({
  components: {
    TestcaseContent,
    ArrowLeft,
  },
  setup() {
    const formValue = ref({});

    const getData = () => {
      getCaseDetail(testcaseTable.rowData.value.id)
        .then((res) => {
          formValue.value = res.data;
        })
        .catch(() => {
          window.$message?.error('无法获取数据');
        });
    };

    watch(testcaseTable.active, () => {
      if (testcaseTable.active.value) {
        getData();
      }
    });

    return {
      active: testcaseTable.active,
      rowData: testcaseTable.rowData,
      formValue,
      getData,
    };
  },
});
</script>
