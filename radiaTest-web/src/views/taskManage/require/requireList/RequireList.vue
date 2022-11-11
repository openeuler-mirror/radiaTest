<template>
  <div
    class="require-item-container acceptable"
    v-for="(item) in props.data"
    :key="`${item.id}_${item.update_time}`"
    :id="item.title"
    @mouseleave="handleLeaveItem(item)"
  >
    <require-item
      @item-click="handleClickItem(item)"
      :item="item"
    />
  </div>
</template>

<script setup>
import requireItem from './requireItem/RequireItem';

const props = defineProps({
  data: {
    type: Array,
    default: () => [],
  }
});

function getButtonsNum(el) {
  const [buttonContainer] = el.getElementsByClassName('button-container');
  return buttonContainer.childElementCount;
}

function handleClickItem(item) {
  const el = document.getElementById(item.title);
  const buttonsNum = getButtonsNum(el);
  let className = 'slide-one';
  if (buttonsNum === 2) {
    className = 'slide-two';
  } else if (buttonsNum === 3) {
    className = 'slide-three';
  }

  !el.classList.contains(className) && el.classList.contains('acceptable')
    ? el.classList.add(className)
    : el.classList.remove(className);
}
function handleLeaveItem(item) {
  const el = document.getElementById(item.title);
  el.classList.remove('slide-one');
  el.classList.remove('slide-two');
  el.classList.remove('slide-three');
}
</script>

<style scoped lang="less">
.slide-one {
  transform: translateX(-50px);
}
.slide-two {
  transform: translateX(-100px);
}
.slide-three {
  transform: translateX(-150px);
}
.require-item-container {
  border-bottom: 1px solid #efeff4;
  transition: all 1s;
}
.require-item-container.acceptable:hover {
  cursor: pointer;
}
.require-item-container.unacceptable {
  background-color: rgba(250, 250, 252, 1);
}
.unacceptable {
  :deep(.require-item) {
    .require-item-header {
      .title {
        color: #929292;
      }
      .subtitle {
        .info {
          .var {
            color: #929292;
          }
        }
      }
    }
    .require-item-footer {
      .info {
        .var {
          color: #929292;
        }
      }
    }
  }
}
</style>
