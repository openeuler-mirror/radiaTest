<template>
  <n-card hoverable>
    <n-space vertical>
      <n-tabs animated type="line">
        <n-tab-pane name="configs" tab="概览" v-if="data.ip">
          <n-grid x-gap="24" y-gap="48">
            <n-gi :span="24"></n-gi>
            <n-gi :span="6">
              <n-space vertical>
                <n-p>
                  <span>内存：</span>
                  <n-button
                    color="#2080F0"
                    text
                    @click="() => editModalRef.changeShow('memory')"
                  >
                    {{ data.memory }} MB
                  </n-button>
                </n-p>
                <n-p>
                  <span>vCPUs：</span>
                  <n-button
                    color="#2080F0"
                    text
                    @click="() => editModalRef.changeShow('vcpus')"
                  >
                    {{ data.sockets * data.cores * data.threads }}
                  </n-button>
                </n-p>
                <n-p>
                  <span>Boot顺序：</span>
                  <n-button color="#2080F0" text @click="handleBootClick">
                    disk
                  </n-button>
                </n-p>
                <n-p>
                  <span>Model：</span>
                  <span>{{ data.cpu_mode }}</span>
                </n-p>
                <n-p>
                  <span>VNC端口：</span>
                  <span>{{ data.vnc_port }}</span>
                </n-p>
              </n-space>
            </n-gi>
            <n-gi :span="10">
              <n-space vertical>
                <n-p>操作系统：{{ osInfo }}</n-p>
                <n-p>系统内核：{{ kernelInfo }}</n-p>
                <n-p>
                  <span>特殊配置：</span>
                  <n-button
                    color="#2080F0"
                    text
                    :disabled="
                      data.special_device
                        ? data.special_device.split(',').length ===
                          specialDevice.length
                        : false
                    "
                    @click="editModalRef.changeShow('device')"
                  >
                    添加
                  </n-button>
                </n-p>
                <n-tag
                  v-for="(item, i) in data.special_device
                    ? data.special_device.split(',')
                    : []"
                  :key="i"
                  type="success"
                >
                  {{ item }}
                </n-tag>
                <ssh-info :machine-id="data.id" />
                <n-p>
                  <span>SSH端口：</span>
                  <span>{{ data.port }}</span>
                </n-p>
              </n-space>
            </n-gi>
            <n-gi :span="4">
              <n-space vertical>
                <n-progress
                  type="circle"
                  :stroke-width="10"
                  :percentage="memoryPercentage"
                />
                <n-p class="usageText">内存用量</n-p>
              </n-space>
            </n-gi>
            <n-gi :span="4">
              <n-space vertical>
                <n-progress
                  type="circle"
                  :stroke-width="10"
                  :percentage="cpuPercentage"
                />
                <n-p class="usageText">CPU用量</n-p>
              </n-space>
            </n-gi>
            <n-gi :span="24"></n-gi>
          </n-grid>
          <edit-modal
            ref="editModalRef"
            :data="data"
            @refresh="() => context.emit('change')"
          />
        </n-tab-pane>
        <n-tab-pane name="nics" tab="网卡配置" v-if="data.ip">
          <div
            style="
              width: 100%;
              display: flex;
              justify-content: end;
              margin-bottom: 10px;
            "
          >
            <n-button
              type="primary"
              style="margin-right: 5%"
              ghost
              @click="createModalNic.show()"
            >
              添加网卡
            </n-button>
            <modal-card
              title="添加网卡"
              url="/v1/vnic"
              ref="createModalNic"
              @validate="() => createFormNic.handlePropsButtonClick()"
              @submit="createFormNic.post()"
            >
              <template #form>
                <nics-form
                  ref="createFormNic"
                  :id="data.id"
                  :name="data.name"
                  @valid="() => createModalNic.submitCreateForm()"
                  @close="
                    () => {
                      createModalNic.close();
                    }
                  "
                />
              </template>
            </modal-card>
          </div>
          <nics-data-table :id="data.id" ref="nics" />
        </n-tab-pane>
        <n-tab-pane name="disks" tab="硬盘配置" v-if="data.ip">
          <div
            style="
              width: 100%;
              display: flex;
              justify-content: end;
              margin-bottom: 10px;
            "
          >
            <n-button
              type="primary"
              style="margin-right: 5%"
              ghost
              @click="createModalDisk.show()"
            >
              添加磁盘
            </n-button>
            <modal-card
              title="添加磁盘"
              url="/v1/vdisk"
              ref="createModalDisk"
              @validate="() => createFormDisk.handlePropsButtonClick()"
              @submit="createFormDisk.post()"
            >
              <template #form>
                <disks-form
                  ref="createFormDisk"
                  :id="data.id"
                  :name="data.name"
                  @valid="() => createModalDisk.submitCreateForm()"
                  @close="
                    () => {
                      createModalDisk.close();
                    }
                  "
                />
              </template>
            </modal-card>
          </div>
          <disks-data-table :id="data.id" ref="disks" />
        </n-tab-pane>
        <n-tab-pane name="consoles" tab="控制台">
          <div v-if="data.status === 'shut off'">
            请开启该虚拟机以连接其控制台
          </div>
          <div v-else>
            <console :data="data" />
          </div>
        </n-tab-pane>
      </n-tabs>
    </n-space>
    <div
      style="
        position: absolute;
        top: 0;
        right: 0;
        margin-top: 25px;
        margin-right: 20px;
      "
    >
      <buttons
        :status="data.status"
        :id="data.id"
        @change="() => handleChange(memoryPercentage, cpuPercentage)"
      />
    </div>
  </n-card>
</template>

<script>
import { ref, watch, onMounted, onBeforeUnmount, defineComponent } from 'vue';
import { Socket } from '@/socket';
import settings from '@/assets/config/settings.js'; 

import SshInfo from './expandedContent/SshInfo.vue';
import ModalCard from '@/components/CRUD/ModalCard.vue';
import EditModal from '@/components/vmachineComponents/expandedContent/EditModal.vue';

import { specialDevice } from '@/assets/config/vmachineSpecialDevice.js';
import expandedContent from './expandedContent';
import expanded from '@/views/vmachine/modules/expanded.js';
import { getVmachineSsh } from '@/api/get.js';

export default defineComponent({
  components: {
    ...expandedContent,
    ModalCard,
    EditModal,
    SshInfo,
  },
  props: {
    data: Object,
  },
  // eslint-disable-next-line max-lines-per-function
  setup(props, context) {
    const SshUser = ref('');
    const SshPassword = ref('');
    const vmachineResourceSocket = new Socket(
      `${settings.websocketProtocol}://${props.data.machine_group.messenger_ip}:${props.data.machine_group.messenger_listen}/monitor/normal`
    );
    vmachineResourceSocket.connect();
    const memoryPercentage = ref('');
    const cpuPercentage = ref('');
    const osInfo = ref('');
    const kernelInfo = ref('');
    onMounted(() => {
      getVmachineSsh(props.data.id).then((res) => {
        SshUser.value = res.data.user;
        SshPassword.value = res.data.password;
        if (props.data.status === 'running') {
          vmachineResourceSocket.emit('start', {
            ip: props.data.ip,
            port: props.data.port,
            user: SshUser.value,
            password: SshPassword.value,
          });
        }
        vmachineResourceSocket.listen(props.data.ip, (data) => {
          data.mem_usage
            ? (memoryPercentage.value = data.mem_usage.toFixed(2))
            : 0;
          data.cpu_usage ? (cpuPercentage.value = data.cpu_usage.toFixed(2)) : 0;
          osInfo.value = data.os_info;
          kernelInfo.value = data.kernel_info;
        });
      }).catch(() => {
        window.$message?.warning('无权获取ssh信息，无法通过概览获取CPU与内存用量数据');
      });
    });
    onBeforeUnmount(() => {
      vmachineResourceSocket.emit('end', props.data.ip);
      memoryPercentage.value = '';
      cpuPercentage.value = '';
      vmachineResourceSocket.disconnect();
      SshUser.value = '';
      SshPassword.value = '';
    });
    watch(
      () => props.data.status,
      () => {
        if (
          props.data.status === 'shut off' ||
          props.data.status === 'paused'
        ) {
          vmachineResourceSocket.emit('end', props.data.ip);
          memoryPercentage.value = '';
          cpuPercentage.value = '';
        } else if (props.data.status === 'running') {
          vmachineResourceSocket.emit('start', {
            ip: props.data.ip,
            port: props.data.port,
            user: props.data.user,
            password: props.data.password,
          });
        }
      }
    );
    return {
      memoryPercentage,
      cpuPercentage,
      osInfo,
      kernelInfo,
      context,
      specialDevice,
      ...expanded,
    };
  },
});
</script>

<style scoped>
.memoryUse {
  font-size: 25px;
}
.usageText {
  position: relative;
  left: 32px;
}
</style>
