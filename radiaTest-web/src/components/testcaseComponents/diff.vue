<template>
  <CodeDiff
    outputFormat="side-by-side"
    :fileName="info.name"
    :drawFileList="true"
    :old-string="info.oldContent"
    :new-string="info.newContent"
  />
</template>
<script>
import { CodeDiff } from 'v-code-diff';
export default {
  props:['info'],
  components: {
    CodeDiff,
  },
};
</script>
