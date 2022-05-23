<template>
  <n-card class="mirror-card" :style="{ width: width }" hoverable>
    <n-space vertical>
      <n-tabs type="line" justify-content="space-evenly">
        <n-tab-pane name="iso" tab="ISO文件">
          <n-grid :cols="24" y-gap="12">
            <n-gi :span="24"></n-gi>
            <n-gi :span="4"></n-gi>
            <n-gi :span="19">
              <n-list style="width: 80%">
                <n-list-item>
                  <template #suffix>
                    <n-button
                      v-if="!data.iso.aarch64.url"
                      type="success"
                      @click="handleCreateClick(form.id, 'iso', 'aarch64')"
                      text
                    >
                      注册
                    </n-button>
                    <n-button
                      v-if="data.iso.aarch64.url"
                      type="primary"
                      @click="handleUpdateClick(form.id, 'iso', 'aarch64')"
                      text
                    >
                      修改
                    </n-button>
                  </template>
                  <n-thing title="aarch64架构" class="thing">
                    <p style="position: relative; left: 40px">
                      <span>URL：</span>
                      <span class="info">{{ data.iso.aarch64.url }} </span>
                      <br /><br />
                      <span>kickstart: </span>
                      <span class="info">{{ data.iso.aarch64.ks }}</span>
                      <br /><br />
                      <span>grub.efi: </span>
                      <span class="info">{{ data.iso.aarch64.efi }}</span>
                      <br /><br />
                      <span>location: </span>
                      <span class="info">{{ data.iso.aarch64.location }}</span>
                    </p>
                  </n-thing>
                </n-list-item>
                <n-list-item>
                  <template #suffix>
                    <n-button
                      v-if="!data.iso.x64.url"
                      type="success"
                      @click="handleCreateClick(form.id, 'iso', 'x86_64')"
                      text
                    >
                      注册
                    </n-button>
                    <n-button
                      v-if="data.iso.x64.url"
                      type="primary"
                      @click="handleUpdateClick(form.id, 'iso', 'x86_64')"
                      text
                    >
                      修改
                    </n-button>
                  </template>
                  <n-thing title="x86_64架构" class="thing">
                    <p style="position: relative; left: 40px">
                      <span>URL：</span>
                      <span class="info">{{ data.iso.x64.url }} </span>
                      <br /><br />
                      <span>kickstart: </span>
                      <span class="info">{{ data.iso.x64.ks }}</span>
                      <br /><br />
                      <span>grub.efi: </span>
                      <span class="info">{{ data.iso.x64.efi }}</span>
                      <br /><br />
                      <span>location: </span>
                      <span class="info">{{ data.iso.x64.location }}</span>
                    </p>
                  </n-thing>
                </n-list-item>
              </n-list>
            </n-gi>
          </n-grid>
        </n-tab-pane>
        <n-tab-pane name="qcow2" tab="qcow2文件">
          <n-grid :cols="24" y-gap="12">
            <n-gi :span="24"></n-gi>
            <n-gi :span="4"></n-gi>
            <n-gi :span="19">
              <n-list style="width: 80%">
                <n-list-item>
                  <template #suffix>
                    <n-button
                      v-if="!data.qcow2.aarch64.url"
                      type="success"
                      @click="handleCreateClick(form.id, 'qcow2', 'aarch64')"
                      text
                    >
                      注册
                    </n-button>
                    <n-button
                      v-if="data.qcow2.aarch64.url"
                      type="primary"
                      @click="handleUpdateClick(form.id, 'qcow2', 'aarch64')"
                      text
                    >
                      修改
                    </n-button>
                  </template>
                  <n-thing title="aarch64架构" class="thing">
                    <p style="position: relative; left: 40px">
                      <span>URL：</span>
                      <span class="info">{{ data.qcow2.aarch64.url }}</span>
                      <br /><br />
                      <span>SSH用户名：</span>
                      <span class="info">{{ data.qcow2.aarch64.user }}</span>
                      <br />
                      <span>SSH端口：</span>
                      <span class="info">{{ data.qcow2.aarch64.port }}</span>
                      <br />
                      <span>SSH密码：</span>
                      <span class="info">
                        {{ data.qcow2.aarch64.password }}
                      </span>
                    </p>
                  </n-thing>
                </n-list-item>
                <n-list-item>
                  <template #suffix>
                    <n-button
                      v-if="!data.qcow2.x64.url"
                      type="success"
                      @click="handleCreateClick(form.id, 'qcow2', 'x86_64')"
                      text
                    >
                      注册
                    </n-button>
                    <n-button
                      v-if="data.qcow2.x64.url"
                      type="primary"
                      @click="handleUpdateClick(form.id, 'qcow2', 'x86_64')"
                      text
                    >
                      修改
                    </n-button>
                  </template>
                  <n-thing title="x86_64架构" class="thing">
                    <p style="position: relative; left: 40px">
                      <span>URL：</span>
                      <span class="info">{{ data.qcow2.x64.url }}</span>
                      <br /><br />
                      <span>SSH用户名：</span>
                      <span class="info">{{ data.qcow2.x64.user }}</span>
                      <br />
                      <span>SSH端口：</span>
                      <span class="info">{{ data.qcow2.x64.port }}</span>
                      <br />
                      <span>SSH密码：</span>
                      <span class="info">
                        {{ data.qcow2.x64.password }}
                      </span>
                    </p>
                  </n-thing>
                </n-list-item>
              </n-list>
            </n-gi>
          </n-grid>
        </n-tab-pane>
      </n-tabs>
    </n-space>
  </n-card>
  <modal-card
    title="注册镜像"
    ref="createModalRef"
    @validate="() => createFormRef.handlePropsButtonClick()"
    @submit="createFormRef.post()"
  >
    <template #form>
      <image-create-form
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
    title="修改镜像"
    ref="updateModalRef"
    @validate="() => updateFormRef.handlePropsButtonClick()"
    @submit="updateFormRef.put()"
  >
    <template #form>
      <image-update-form
        ref="updateFormRef"
        @valid="() => updateModalRef.submitCreateForm()"
        @close="
          () => {
            updateModalRef.close();
          }
        "
      />
    </template>
  </modal-card>
</template>

<script>
import { toRefs, onMounted, onUnmounted, defineComponent } from 'vue';
import { Socket } from '@/socket';

import ModalCard from '@/components/CRUD/ModalCard.vue';
import ImageForm from '@/components/milestoneComponents/milestoneImageForm';

import settings from '@/assets/config/settings';
import imagesCard from '@/views/milestone/modules/images/imagesCard.js';
import {
  getData,
  devideIsoData,
  devideQcow2Data,
} from '@/views/milestone/modules/images/imagesAjax.js';

export default defineComponent({
  components: {
    ModalCard,
    ...ImageForm,
  },
  props: {
    form: Object,
    width: {
      default: '100%',
      type: String,
    },
  },
  setup(props) {
    const { form } = toRefs(props);
    const isoSocket = new Socket(`${settings.websocketProtocol}://${settings.serverPath}/imirroring`);
    const qcow2Socket = new Socket(`${settings.websocketProtocol}://${settings.serverPath}/qmirroring`);
    isoSocket.connect();
    qcow2Socket.connect();

    onMounted(() => {
      getData(form, imagesCard.data);
      isoSocket.listen('update', (res) => {
        const thisData = JSON.parse(res).filter(
          (item) => item.milestone_id === form.value.id
        );
        devideIsoData(thisData, imagesCard.data);
      });
      qcow2Socket.listen('update', (res) => {
        const thisData = JSON.parse(res).filter(
          (item) => item.milestone_id === form.value.id
        );
        devideQcow2Data(thisData, imagesCard.data);
      });
    });

    onUnmounted(() => {
      imagesCard.clean();
    });

    return {
      ...imagesCard,
    };
  },
});
</script>

<style scoped>
.mirror-card {
  margin-bottom: 20px;
}
.port {
  position: relative;
  left: 200px;
}
.url {
  position: relative;
  left: 600px;
}
.thing {
  font-size: 12px;
}
.info {
  color: #0217af;
}
</style>
