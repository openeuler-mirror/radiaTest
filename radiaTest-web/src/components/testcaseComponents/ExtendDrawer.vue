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
import { ref, watch, defineComponent, getCurrentInstance } from 'vue';

import { ArrowLeft32Filled as ArrowLeft } from '@vicons/fluent';
import TestcaseContent from './TestcaseContent.vue';

import testcaseTable from '@/views/caseManage/testcase/modules/testcaseTable.js';

export default defineComponent({
  components: {
    TestcaseContent,
    ArrowLeft,
  },
  setup() {
    const { proxy } = getCurrentInstance();
    const formValue = ref({});

    const getData = () => {
      proxy.$axios
        .get('/v1/case', {
          id: testcaseTable.rowData.value.id,
          name: testcaseTable.rowData.value.name,
        })
        .then((res) => {
          if (!res.error_mesg && res) {
            [formValue.value] = res;
          } else {
            window.$message?.error(res.error_mesg);
          }
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
