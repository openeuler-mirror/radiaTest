<template>
  <n-card
    title="模板仓库"
    size="huge"
    :segmented="{
      content: 'hard',
    }"
    header-style="
            font-size: 30px;
            height: 80px;
            font-family: 'v-sans';
            padding-top: 40px;
            background-color: rgb(242,242,242);
        "
  >
    <div style="display: flex; flex-wrap: nowrap">
      <div
        style="width: calc(100% - 180px); display: block; margin-right: 36px"
      >
        <template-card type="task" id="taskTemp" />
        <template-card type="personal" id="personalTemp" />
        <template-card type="team" id="teamTemp" />
        <template-card type="orgnization" id="orgTemp" />
      </div>
      <div style="width: 144px; display: block">
        <n-anchor
          affix
          :trigger-top="24"
          :top="88"
          style="z-index: 1; position: fixed"
          :bound="24"
          offset-target="#homeBody"
        >
          <n-anchor-link title="任务模板" href="#taskTemp" />
          <n-anchor-link title="个人模板" href="#personalTemp" />
          <n-anchor-link title="团队模板" href="#teamTemp" />
          <n-anchor-link title="组织模板" href="#orgTemp" />
        </n-anchor>
        <n-popover trigger="hover">
          <template #trigger>
            <div
              ref="createButton"
              style="
                position: fixed;
                height: 100px;
                bottom: 360px;
                color: rgba(206, 206, 206, 1);
              "
              @mouseenter="handleHover(createButton)"
              @mouseleave="handleLeave(createButton)"
              @click="createModalRef.show()"
            >
              <n-icon :size="80">
                <create />
              </n-icon>
            </div>
          </template>
          <span>新建模板</span>
        </n-popover>
        <modal-card
          :init-x="400"
          :init-y="100"
          url="/template"
          ref="createModalRef"
          @validate="() => createFormRef.handlePropsButtonClick()"
          @submit="createFormRef.post()"
        >
          <template #form>
            <template-create-form
              ref="createFormRef"
              @valid="() => createModalRef.submitCreateForm()"
              @close="
                () => {
                  createModalRef.close();
                }
              "
            />
          </template>
        </modal-card>
        <modal-card
          :title="执行模板"
          :init-x="400"
          :init-y="100"
          ref="execModalRef"
          @validate="postExecData()"
        >
          <template #form>
            <exec-template />
          </template>
        </modal-card>
        <n-popover trigger="hover">
          <template #trigger>
            <div
              ref="copyButton"
              style="
                position: fixed;
                height: 100px;
                bottom: 200px;
                color: rgba(206, 206, 206, 1);
              "
              @mouseenter="handleHover(copyButton)"
              @mouseleave="handleLeave(copyButton)"
              @click="handleCloneClick"
            >
              <n-icon :size="80">
                <copy />
              </n-icon>
            </div>
          </template>
          <span>克隆模板</span>
        </n-popover>
      </div>
    </div>
    <template #action>
      <n-divider />
      <div
        style="
          text-align: center;
          color: grey;
          padding-top: 15px;
          padding-bottom: 0;
        "
      >
        {{ settings.name }} {{ settings.version }} · {{ settings.license }}
      </div>
    </template>
    <n-modal
      v-model:show="showCloneModal"
      preset="dialog"
      title="Dialog"
      :showIcon="false"
      positiveText="提交"
      negativeText="关闭"
      @negativeClick="showCloneModal = false"
      @positiveClick="handleCloneSubmit"
    >
      <template #header>
        <div>克隆模板</div>
      </template>
      <div>
        <n-form ref="cloneForm" :model="cloneFormValue" :rules="cloneFormRule">
          <n-form-item label="模板" path="cloneTemplateRule">
            <n-select
              :options="templateList"
              v-model:value="cloneFormValue.cloneTemplateId"
            />
          </n-form-item>
          <n-form-item label="类型" path="permissionRule">
            <n-cascader
              v-model:value="cloneFormValue.permissionType"
              placeholder="请选择"
              :options="typeOptions"
              check-strategy="child"
              remote
              :on-load="handleLoad"
            />
          </n-form-item>
        </n-form>
      </div>
    </n-modal>
  </n-card>
</template>

<script>
import { provide, onMounted, onUnmounted, defineComponent } from 'vue';

import ModalCard from '@/components/CRUD/ModalCard.vue';
import Essential from '@/components/templateComponents';
import execTemplate from '@/components/templateComponents/execTemplate.vue';
import {
  CollectionsAdd24Filled as Copy,
  DocumentAdd16Filled as Create,
} from '@vicons/fluent';

import { Socket } from '@/socket.js';
import settings from '@/assets/config/settings.js';
import template from './modules/template.js';
import { execModalRef, postExecData } from './modules/execTemplate';
import extendForm from '@/views/product/modules/createForm.js';

export default defineComponent({
  components: {
    ModalCard,
    ...Essential,
    Copy,
    Create,
    execTemplate
  },
  setup() {
    const templateSocket = new Socket(`${settings.websocketProtocol}://${settings.serverPath}/template`);
    templateSocket.connect();

    provide('personal', template.personalData);
    provide('team', template.teamData);
    provide('orgnization', template.orgnizationData);
    provide('task', template.taskData);

    onMounted(() => {
      template.getData();

      templateSocket.listen('update', () => {
        template.getData();
      });
    });

    onUnmounted(() => {
      templateSocket.disconnect();
    });

    return {
      typeOptions: extendForm.typeOptions,
      handleLoad: extendForm.handleLoad,
      settings,
      ...template,
      postExecData,
      execModalRef,
      // handleCloneClick() {
      //   window.$message?.info('克隆功能将于下一个版本更新');
      // },
    };
  },
});
</script>

<style scoped></style>
