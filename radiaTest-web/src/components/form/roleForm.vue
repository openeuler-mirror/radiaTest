<template>
  <modal-card
    :initY="100"
    :title="type === 'create' ? '创建角色' : '修改角色'"
    ref="createRuleModal"
    @validate="submitForm"
    @closeCard="closeForm"
  >
    <template #form>
      <n-form :label-width="80" :model="formValue" :rules="rules" ref="formRef">
        <n-form-item label="名称" path="name">
          <n-input v-model:value="formValue.name" placeholder="请输入" />
        </n-form-item>
        <n-form-item label="角色类型" path="type">
          <n-select
            @update:value="changeType"
            v-model:value="formValue.type"
            :options="roleType"
            placeholder="请选择"
          />
        </n-form-item>
        <n-form-item
          label="所属组织"
          path="org_id"
          v-if="formValue.type && formValue.type !== 'public'"
        >
          <n-select
            @update:value="changeOrg"
            :value="formValue.org_id"
            :options="orgs"
            placeholder="请选择"
          />
        </n-form-item>
        <n-form-item
          label="所属团队"
          path="group_id"
          v-if="formValue.type && formValue.type === 'group' && formValue.org_id"
        >
          <n-select
            v-model:value="formValue.group_id"
            :options="groups"
            @update:value="groupChange"
            placeholder="请选择"
          />
        </n-form-item>
        <n-form-item label="继承已有角色" v-if="roles.length">
          <n-radio-group v-model:value="formValue.role_id" name="radiogroup">
            <n-space>
              <n-radio v-for="role in roles" :key="role.value" :value="role.value">
                {{ role.label }}
              </n-radio>
            </n-space>
          </n-radio-group>
        </n-form-item>
        <n-form-item label="描述">
          <n-input v-model:value="formValue.description" type="textarea" placeholder="请输入" />
        </n-form-item>
      </n-form>
    </template>
  </modal-card>
</template>
<script>
import modalCard from '@/components/CRUD/ModalCard.vue';
import { getExtendRole, getOrgGroup } from '@/api/get';
export default {
  components: {
    modalCard,
  },
  props: {
    type: {
      type: String,
      default: 'create',
    },
    formData: Array,
  },
  methods: {
    setRoles(data) {
      this.roles = [];
      data.forEach((item) => {
        this.roles.push({ label: item.name, value: item.id });
      });
    },
    changeType(value) {
      if (value === 'public') {
        getExtendRole({ type: 'public' }).then((res) => {
          this.setRoles(res.data);
        });
      }
    },
    show() {
      this.$nextTick(() => {
        if (this.type !== 'create') {
          this.formValue = this.formData;
          if (this.formValue.eft === 'allow') {
            this.formValue.eft = true;
          }
        }
        this.$refs.createRuleModal.show();
      });
    },
    changeOrg(value) {
      if (value) {
        this.formValue.org_id = value;
        this.getGroups();
        if (this.formValue.type === 'organization') {
          getExtendRole({ type: 'org', org_id: this.formValue.org_id }).then((res) => {
            this.setRoles(res.data);
          });
        }
      }
    },
    groupChange(value) {
      if (value && this.formValue.type === 'group') {
        getExtendRole({
          type: 'group',
          group_id: this.formValue.group_id,
          org_id: this.formValue.org_id,
        }).then((res) => {
          this.setRoles(res.data);
        });
      }
    },
    getOrg() {
      this.$axios
        .get('/v1/orgs/all', { page_size: 99999, page_num: 1 })
        .then((res) => {
          this.orgs = res.data.items?.map((item) => ({
            label: item.name,
            value: String(item.id),
          }));
        })
        .catch((err) => window.message?.error(err.data.error_msg || '未知错误'));
    },
    getGroups() {
      getOrgGroup(this.formValue.org_id, {
        page_num: 1,
        page_size: 99999,
      })
        .then((res) => {
          this.groups = res.data.items.map((item) => ({
            label: item.name,
            value: String(item.id),
          }));
        })
        .catch((err) => window.message?.error(err.data.error_msg || '未知错误'));
    },
    initFormValue() {
      this.formValue = {
        name: '',
        type: null,
        org_id: null,
        group_id: null,
        description: '',
      };
    },
    submitForm() {
      this.$refs.formRef.validate((errors) => {
        if (!errors) {
          const data = JSON.parse(JSON.stringify(this.formValue));
          this.initFormValue();
          this.$refs.createRuleModal.close();
          this.$emit('submitform', { data, type: this.type });
        } else {
          window.$message?.error('填写信息有误，请检查');
        }
      });
    },
    closeForm() {
      this.initFormValue();
    },
  },
  mounted() {
    this.getOrg();
  },
  data() {
    return {
      roles: [],
      formValue: {
        name: '',
        type: null,
        org_id: null,
        group_id: null,
        description: '',
        role_id: '',
      },
      roleType: [
        { label: '公共角色', value: 'public' },
        { label: '团队角色', value: 'group' },
        { label: '组织角色', value: 'organization' },
      ],
      orgs: [],
      groups: [],
      rules: {
        name: {
          trigger: ['input', 'blur'],
          required: true,
          message: '请填写名称',
        },
        type: {
          trigger: ['change', 'blur'],
          required: true,
          message: '请选择类型',
        },
        org_id: {
          trigger: ['change', 'blur'],
          required: true,
          message: '请选择组织',
        },
        group_id: {
          trigger: ['change', 'blur'],
          required: true,
          message: '请选择用户组',
        },
      },
    };
  },
  setup() {
    return {
      railStyle: ({ focused, checked }) => {
        const style = {};
        if (checked) {
          style.background = '#d03050';
          if (focused) {
            style.boxShadow = '0 0 0 2px #d0305040';
          }
        } else {
          style.background = '#2080f0';
          if (focused) {
            style.boxShadow = '0 0 0 2px #2080f040';
          }
        }
        return style;
      },
    };
  },
};
</script>
