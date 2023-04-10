<template>
  <n-tabs animated default-value="cla" size="large" justify-content="space-evenly">
    <n-tab-pane name="cla" tab="CLA">
      <n-table :single-line="false">
        <tbody>
          <tr>
            <td>cla签署地址</td>
            <td>{{ info.cla_sign_url }}</td>
          </tr>
          <tr>
            <td>cla验证地址</td>
            <td>{{ info.cla_verify_url }}</td>
          </tr>
          <tr>
            <td>验证地址的请求方式</td>
            <td>{{ info.cla_request_type }}</td>
            <td>验证通过的标志</td>
            <td>{{ info.cla_pass_flag }}</td>
          </tr>
          <tr>
            <td>cla验证参数</td>
            <td>{{ info.cla_verify_params }}</td>
            <td>body中的参数</td>
            <td>{{ info.cla_verify_body }}</td>
          </tr>
        </tbody>
      </n-table>
    </n-tab-pane>
    <n-tab-pane name="type" :tab="tabName">
      <n-table :single-line="false">
        <tbody>
          <tr>
            <td>oauth_login_url</td>
            <td>{{ info.oauth_login_url }}</td>
          </tr>
          <tr>
            <td>oauth_client_id</td>
            <td>{{ info.oauth_client_id }}</td>
          </tr>
          <tr>
            <td>oauth_client_secret</td>
            <td>{{ info.oauth_client_secret }}</td>
          </tr>
          <tr>
            <td>oauth_scope</td>
            <td>{{ info.oauth_scope }}</td>
          </tr>
          <tr>
            <td>oauth_get_token_url</td>
            <td>{{ info.oauth_get_token_url }}</td>
          </tr>
          <tr>
            <td>oauth_get_user_info_url</td>
            <td>{{ info.oauth_get_user_info_url }}</td>
          </tr>
          <tr v-if="tabName === '企业应用'">
            <td>Gitee企业仓ID</td>
            <td>{{ info.enterprise_id }}</td>
          </tr>
        </tbody>
      </n-table>
    </n-tab-pane>
  </n-tabs>
</template>

<script setup>
const props = defineProps(['info']);
const { info } = toRefs(props);

const tabName = computed(() => {
  if (info.value.authority === 'oneid') {
    return 'oneid鉴权';
  } else if (info.value.authority === 'gitee' && info.value.enterprise_id) {
    return '企业应用';
  }
  return '个人应用';
});
</script>
