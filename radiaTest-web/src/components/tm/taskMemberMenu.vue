<template>
  <div class="member-menu">
    <div class="search-content">
      <n-input
        v-model:value="inputValue"
        type="text"
        placeholder="搜索"
        @input="search"
      />
    </div>
    <div class="selectable-selection">
      <n-scrollbar style="max-height: 300px">
        <ul class="member-list">
          <li class="select-option-group">
            <div class="option-group-label">
              {{ renderLabel(type) }}
            </div>
            <ul v-if="!multiple">
              <li
                class="member-menu-item"
                v-for="(value, index) in personArray"
                :key="index"
                @click="selectPerson(value)"
              >
                <span><img :src="value.avatar" /></span>
                <div class="item-content-wrap">
                  <div class="item-content">
                    <div class="item-main">
                      <div class="item-name">{{ value.name }}</div>
                    </div>
                  </div>
                </div>
              </li>
            </ul>
            <ul v-else>
              <n-checkbox-group v-model:value="groupValue">
                <div
                  v-for="(value, index) in personArray"
                  :key="index"
                  class="member-menu-item"
                >
                  <n-checkbox :value="JSON.stringify(value)">
                    <div style="display: flex">
                      <span><img :src="value.avatar" /></span>
                      <div class="item-content-wrap">
                        <div class="item-content">
                          <div class="item-main">
                            <div class="item-name">{{ value.name }}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </n-checkbox>
                </div>
              </n-checkbox-group>
            </ul>
          </li>
        </ul>
      </n-scrollbar>
    </div>
    <n-divider style="margin: 4px 0" />
    <div class="footer" v-show="multiple">
      <n-button type="info" @click="confirm" class="btn">确定</n-button>
    </div>
  </div>
</template>

<script>
import { getGroup } from '@/api/get';
export default {
  props: [
    'multiple',
    'defaultValue',
    'id',
    'type',
    'executorType',
    'groupId',
    'originator',
  ],
  data() {
    return {
      personArray: [],
      personArrayTemp: [],
      inputValue: null,
      groupValue: null,
    };
  },
  methods: {
    renderLabel(_type) {
      if (_type === 'PERSON' || _type === 'ORGANIZATION') {
        return '人员';
      } else if (_type === 'GROUP') {
        return '团队';
      }
      return '人员/团队';
    },
    getGroupUser() {
      return new Promise((resolve, reject) => {
        const id = this.groupId;
        this.$axios
          .get(`/v1/groups/${id}/users`, {
            page_size: 99999,
            page_num: 1,
          })
          .then((res) => {
            for (const item of res.data.items) {
              const element = {
                id: item.gitee_id,
                avatar: item.avatar_url,
                name: item.gitee_name,
                type: 'PERSON',
              };
              this.personArrayTemp.push(element);
              this.personArray.push(element);
            }
            resolve();
          })
          .catch((err) => {
            window.$message?.error(err.data.error_msg || '未知错误');
            reject(Error('error'));
          });
      });
    },
    getOrgUser() {
      return new Promise((resolve, reject) => {
        const id = this.$storage.getValue('loginOrgId');
        this.$axios
          .get(`/v1/org/${id}/users`, {
            page_size: 99999,
            page_num: 1,
          })
          .then((res) => {
            for (const item of res.data.items) {
              const element = {
                id: item.gitee_id,
                avatar: item.avatar_url,
                name: item.gitee_name,
                type: 'PERSON',
              };
              this.personArrayTemp.push(element);
              this.personArray.push(element);
            }
            resolve();
          })
          .catch((err) => {
            window.$message?.error(err.data.error_msg || '未知错误');
            reject(Error('error'));
          });
      });
    },
    getOrgGroup() {
      return new Promise((resolve, reject) => {
        getGroup({
          page_size: 99999,
          page_num: 1,
        })
          .then((res) => {
            for (const item of res.data.items) {
              const element = {
                id: item.id,
                avatar: item.avatar_url,
                name: item.name,
                type: 'GROUP',
              };
              this.personArrayTemp.push(element);
              this.personArray.push(element);
            }
            resolve();
          })
          .catch((err) => {
            window.$message?.error(err.data.error_msg || '未知错误');
            reject(Error('error'));
          });
      });
    },
    selectPerson(value) {
      this.$emit('getPerson', value);
    },
    confirm() {
      this.$emit('getPerson', this.groupValue);
    },
    search() {
      if (!this.inputValue) {
        this.personArray = this.personArrayTemp;
      }
      this.personArray = this.personArray.filter(
        (item) => item.name.indexOf(this.inputValue) !== -1
      );
    },
  },
  mounted() {
    (async () => {
      this.personArray = [];
      this.personArrayTemp = [];
      if (this.type === 'PERSON') {
        await this.getGroupUser();
      } else if (this.type === 'GROUP') {
        await this.getOrgGroup();
      } else if (this.type === 'ORGANIZATION') {
        await this.getOrgUser();
      } else if (this.type === 'ALL') {
        await this.getOrgUser();
        await this.getOrgGroup();
      }
      if (this.multiple) {
        this.groupValue = this.defaultValue.map((item) => {
          const element = this.personArray.find((i) => {
            if (item.name) {
              return i.id === item.participant_id && i.name === item.name;
            }
            return i.id === item.gitee_id && i.name === item.gitee_name;
          });
          console.log(element);
          return JSON.stringify(element);
        });
        const index = this.personArray.findIndex((item) => {
          return item.id === this.originator;
        });
        this.personArray.splice(index, 1);
        this.personArrayTemp.splice(index, 1);
      }
    })();
  },
};
</script>

<style lang="less" scoped>
ol,
ul {
  margin: 0;
  padding: 0;
  list-style: none;
}

.selectable-selection {
  display: flex;
  flex: 1;
  min-height: 0%;

  .member-list {
    width: 100%;
    overflow-x: hidden;
    overflow-y: auto;
    position: relative;

    .select-option-group {
      line-height: 20px;
      list-style: none;

      .option-group-label {
        padding: 6px 16px;
        font-size: 14px;
        color: #8c8c8c;
        cursor: auto;
      }

      .member-menu-item {
        display: flex;
        padding: 6px 16px;
        cursor: pointer;
        line-height: 20px;
        list-style: none;
        &:hover {
          background-color: #f7f7f7;
        }

        span {
          margin-left: 10px;
          display: inline-flex;

          img {
            width: 24px;
            height: 24px;
            border-radius: 50%;
          }
        }

        .item-content-wrap {
          margin-left: 12px;
          margin-right: 4px;
          display: flex;
          align-items: center;
          flex: 1;
          overflow: hidden;

          .item-content {
            overflow: hidden;

            .item-main {
              display: flex;
              color: #383838;
              line-height: 18px;

              .item-name {
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
              }
            }
          }
        }

        .item-tick {
          display: flex;
          align-items: center;
          color: #8c8c8c;
        }
      }
    }
  }
}

.footer {
  display: flex;
  justify-content: center;

  .btn {
    width: 85%;
  }
}
</style>
