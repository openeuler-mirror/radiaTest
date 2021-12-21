<template>
  <n-card
    :title="title"
    size="huge"
    :segmented="{content: 'hard',}"
    header-style="
            font-size: 30px;
            height: 80px;
            font-family: 'v-sans';
            padding-top: 40px;
            background-color: #FAFAFC;
          "
    style="height: 100%"
  >
    <slot></slot>
  </n-card>
</template>
<script>
export default {
  props: {
    title: {
      type: String,
      default: ''
    }
  },
  setup () {

  },
};
</script>
