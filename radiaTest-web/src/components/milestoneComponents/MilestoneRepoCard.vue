<template>
  <n-card class="repo-card" :style="{ width: width }" hoverable>
    <n-tabs v-model:value="tabValue" type="line" justify-content="space-evenly">
      <n-tab-pane name="aarch64" tab="aarch64">
        <div v-if="!loading">
          <div v-if="repo['aarch64'] && repo['aarch64'].content">
            <div v-show="!edit['aarch64']">
              <n-code :code="repo['aarch64'].content" language="ini" />
              <n-button
                type="warning"
                style="width: 100%; margin-top: 10px"
                @click="handleEditClick('aarch64')"
              >
                修改repo配置
              </n-button>
            </div>
            <div v-show="edit['aarch64']">
              <n-input
                v-model:value="content['aarch64']"
                type="textarea"
                :autosize="{
                  minRows: 20,
                }"
              />
              <n-space justify="center" style="margin-top: 10px">
                <n-button
                  type="success"
                  @click="handleEditSubmit(form.id, 'aarch64')"
                >
                  提交
                </n-button>
                <n-button type="error" @click="handleEditClick('aarch64')">
                  取消
                </n-button>
              </n-space>
            </div>
          </div>
          <div v-else>
            <n-input
              v-model:value="content['aarch64']"
              type="textarea"
              :autosize="{
                minRows: 20,
              }"
            />
            <n-button
              type="success"
              style="width: 100%; margin-top: 10px"
              @click="handleCreateClick(form.id, 'aarch64')"
            >
              写入新repo配置
            </n-button>
          </div>
        </div>
        <div v-else style="text-align: center">
          <n-spin size="huge" />
        </div>
      </n-tab-pane>
      <n-tab-pane name="x86_64" tab="x86_64">
        <div v-if="!loading">
          <div v-if="repo['x86_64'] && repo['x86_64'].content">
            <div v-show="!edit['x86_64']">
              <n-code :code="repo['x86_64'].content" language="ini" />
              <n-button
                type="warning"
                style="width: 100%; margin-top: 10px"
                @click="handleEditClick('x86_64')"
              >
                修改repo配置
              </n-button>
            </div>
            <div v-show="edit['x86_64']">
              <n-input
                v-model:value="content['x86_64']"
                type="textarea"
                :autosize="{
                  minRows: 20,
                }"
              />
              <n-space justify="center" style="margin-top: 10px">
                <n-button
                  type="success"
                  @click="handleEditSubmit(form.id, 'x86_64')"
                >
                  提交
                </n-button>
                <n-button type="error" @click="handleEditClick('x86_64')">
                  取消
                </n-button>
              </n-space>
            </div>
          </div>
          <div v-else>
            <n-input
              v-model:value="content['x86_64']"
              type="textarea"
              :autosize="{
                minRows: 20,
              }"
            />
            <n-button
              type="success"
              style="width: 100%; margin-top: 10px"
              @click="handleCreateClick(form.id, 'x86_64')"
            >
              写入新repo配置
            </n-button>
          </div>
        </div>
        <div v-else style="text-align: center">
          <n-spin size="huge" />
        </div>
      </n-tab-pane>
    </n-tabs>
  </n-card>
</template>

<script>
import { watch, onMounted, onUnmounted, defineComponent } from 'vue';
import { Socket } from '@/socket';

import settings from '@/assets/config/settings';
import repoCard from '@/views/milestone/modules/repo/repoCard.js';
import repoAjax from '@/views/milestone/modules/repo/repoAjax.js';

export default defineComponent({
  props: {
    form: Object,
    width: {
      type: String,
      default: '100%',
    },
  },
  setup(props) {
    const repoSocket = new Socket(`ws://${settings.serverPath}/repo`);
    repoSocket.connect();

    watch(repoCard.tabValue, () => {
      repoAjax.getcode(props.form.id, repoCard.tabValue.value);
    });

    onMounted(() => {
      repoAjax.getcode(props.form.id, 'aarch64');
      repoSocket.listen('update', (res) => {
        const totalData = JSON.parse(res);
        const arm64Repo = totalData.filter(
          (item) =>
            item.milestone_id === props.form.id && item.frame === 'aarch64'
        );
        const x64Repo = totalData.filter(
          (item) =>
            item.milestone_id === props.form.id && item.frame === 'x86_64'
        );
        repoCard.repo.value.aarch64 = arm64Repo;
        repoCard.repo.value.x86_64 = x64Repo;
      });
    });

    onUnmounted(() => {
      repoCard.clean();
    });

    return {
      ...repoCard,
      ...repoAjax,
    };
  },
});
</script>

<style scoped></style>
