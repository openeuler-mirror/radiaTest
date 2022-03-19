<template>
  <n-tabs default-value="cla" size="large" justify-content="space-evenly">
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
    <n-tab-pane name="enterprise" tab="企业仓">
      <n-table :single-line="false">
        <tbody>
          <tr>
            <td>enterpriseID</td>
            <td>{{ info.enterprise_id }}</td>
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
        </tbody>
      </n-table>
    </n-tab-pane>
  </n-tabs>
</template>
<script>
export default {
  props: ['info']
};
</script>
