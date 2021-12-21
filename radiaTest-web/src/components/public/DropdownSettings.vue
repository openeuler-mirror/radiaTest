<template>
  <n-dropdown
    class="dropdown-settings"
    trigger="hover"
    :size="size"
    @select="handleSelect"
    :placement="placement"
    :options="options"
  >
    <n-icon class="settings" size="30" :depth="2">
      <settings-icon />
    </n-icon>
  </n-dropdown>
</template>

<script>
import { defineComponent } from "vue";
import { NDropdown } from "naive-ui";
import { Settings } from "@vicons/ionicons5";

export default defineComponent({
  components: {
    SettingsIcon: Settings,
    NDropdown,
  },
  props: {
    placement: {
      type: String,
      default: "bottom-start",
    },
    options: Object,
    size: String,
  },
  setup(props, context) {
    return {
      handleSelect(key) {
        context.emit("optSelect", key);
      },
    };
  },
});
</script>

<style>
.settings:hover {
  display: inline-block;
  cursor: pointer;
}
.dropdown-settings.n-dropdown-menu {
  width: 200px;
  text-align: center;
}
</style>