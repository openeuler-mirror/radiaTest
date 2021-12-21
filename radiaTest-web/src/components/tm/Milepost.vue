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
      <ul
        class="member-list"
        v-if="!multiple"
      >
        <li class="select-option-group">
          <div class="option-group-label">里程碑</div>
          <ul v-if="milepostArray.length">
            <li
              class="member-menu-item"
              v-for="(value, index) in milepostArray"
              :key="index"
              @click="selectMilepost(value)"
            >
              <div class="item-content-wrap">
                <div class="item-content">
                  <div class="item-main">
                    <div class="item-name">{{ value.name }}</div>
                  </div>
                </div>
              </div>
            </li>
          </ul>
          <div v-else>
            <n-empty description="无数据"></n-empty>
          </div>
        </li>
      </ul>
      <ul v-else>
        <n-checkbox-group v-model:value="groupValue">
          <div
            v-for="(value, index) in milepostArray"
            :key="index"
            class="member-menu-item"
          >
            <n-checkbox :value="value.id">
              <div style="display:flex">
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
    </div>
    <n-divider style="margin: 4px 0" />
    <div
      class="footer"
      v-show="multiple"
    >
      <n-button
        type="info"
        @click="selectMileposts"
        class="btn"
      >确 定</n-button>
    </div>
  </div>
</template>

<script>
export default {
  props: ['multiple', 'defaultValue'],
  data () {
    return {
      milepostArray: [],
      milepostArrayTemp: [],
      inputValue: null,
      groupValue: null,
    };
  },
  methods: {
    selectMilepost (value) {
      this.$emit('getMilepost', value);
    },
    selectMileposts () {
      this.$emit('getMileposts', this.groupValue);
    },
    search () {
      if (!this.inputValue) {
        this.milepostArray = this.milepostArrayTemp;
      }
      this.milepostArray = this.milepostArrayTemp.filter(
        (item) => item.name.indexOf(this.inputValue) !== -1
      );
    },
  },
  mounted () {
    this.$axios.get('/v1/milestone').then((res) => {
      this.milepostArray = res;
      this.milepostArrayTemp = res;
    });
    if (this.defaultValue) {
      this.groupValue = this.defaultValue.map(item => item.id);
    }
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
