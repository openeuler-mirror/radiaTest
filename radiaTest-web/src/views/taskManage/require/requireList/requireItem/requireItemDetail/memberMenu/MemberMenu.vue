<template>
  <n-popover
    trigger="manual"
    placement="bottom"
    :show="popoverShow"
    @clickoutside="() => { popoverShow = false; }"
  >
    <template #trigger>
      <n-button
        type="info"
        text
        @click="() => { popoverShow = true; }"
      >
        <slot name="label"></slot>
      </n-button>
    </template>
    <taskMemberMenu
      :type="props.type"
      :groupId="props.groupId"
      @getPerson="handleChoose"
    ></taskMemberMenu>
  </n-popover>
</template>

<script setup>
import taskMemberMenu from '@/components/tm/taskMemberMenu';

const props = defineProps({
  type: {
    type: String,
    default: () => 'ORGANIZATION',
  },
  groupId: Number,
});

const emit = defineEmits([ 'choose' ]);

const popoverShow = ref(false);

function handleChoose(user) { 
  popoverShow.value = false;
  emit('choose', user); 
}
</script>

<style scoped lang='less'>
</style>
