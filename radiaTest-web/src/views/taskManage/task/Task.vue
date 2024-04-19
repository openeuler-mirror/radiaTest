<template>
  <n-spin :show="showLoading" stroke="rgba(0, 47, 167, 1)" :style="{ height: '100%' }">
    <div class="task-body">
      <n-drawer
        v-model:show="showNewTaskDrawer"
        :maskClosable="false"
        width="324px"
        placement="left"
      >
        <n-drawer-content title="新建任务" closable>
          <n-form
            :model="model"
            :rules="rules"
            ref="formRef"
            label-placement="left"
            :label-width="80"
            size="medium"
            :style="{}"
          >
            <n-form-item label="名称" path="title">
              <n-input placeholder="请输入任务名称" v-model:value="model.title" />
            </n-form-item>
            <n-form-item label="任务类型" path="type">
              <n-select
                placeholder="请选择"
                :options="taskTypes"
                @update:value="taskTypeChange"
                :value="model.type"
              />
            </n-form-item>
            <n-form-item label="执行团队" path="group_id" v-if="model.type === 'GROUP'">
              <n-select
                placeholder="请选择"
                :options="groups"
                :value="model.group_id"
                :render-label="renderLabel"
                @update:value="getUserByGroup"
                :disabled="model.type == 'PERSON'"
              />
            </n-form-item>
            <n-form-item label="执行者" path="orgTask" v-if="model.type === 'ORGANIZATION'">
              <n-cascader
                :value="model.orgTask"
                placeholder="请选择"
                :options="orgOptions"
                :cascade="false"
                check-strategy="child"
                :show-path="true"
                remote
                @update:value="orgSelect"
                :on-load="handleLoad"
              />
            </n-form-item>
            <n-form-item
              label="执行者"
              path="executor"
              v-if="
                model.type !== null &&
                (model.type === 'GROUP' || model.type === 'PERSON') &&
                model.group !== ''
              "
            >
              <n-select
                placeholder="请选择"
                :options="personArray"
                :render-label="renderLabel"
                :disabled="model.type == 'PERSON'"
                v-model:value="model.executor"
              />
            </n-form-item>
            <n-form-item label="开始日期" path="start_time">
              <n-date-picker type="date" v-model:value="model.start_time" />
            </n-form-item>
            <n-form-item label="截止日期" path="deadline">
              <n-date-picker type="date" v-model:value="model.deadline" />
            </n-form-item>
            <n-form-item label="关键词" path="keywords">
              <n-input placeholder="请输入关键词" v-model:value="model.keywords" type="textarea" />
            </n-form-item>
            <n-form-item label="摘要" path="abstract">
              <n-input
                placeholder="请输入报告摘要"
                v-model:value="model.abstract"
                type="textarea"
              />
            </n-form-item>
            <n-form-item label="缩略语清单" path="abbreviation">
              <n-input
                placeholder="请输入缩略语清单"
                v-model:value="model.abbreviation"
                type="textarea"
              />
            </n-form-item>
            <div class="createButtonBox">
              <n-button class="btn" type="error" ghost @click="cancelCreateTask">取消</n-button>
              <n-button class="btn" type="info" ghost @click="createTask">创建</n-button>
            </div>
            <div class="createButtonBox" style="margin-top: 20px">
              <n-button class="versionTask" type="info" ghost @click="createVersionTask"
                >创建版本任务</n-button
              >
            </div>
          </n-form>
        </n-drawer-content>
      </n-drawer>
      <!-- 泳道视图 -->
      <div v-if="kanban" style="height: 100%">
        <n-scrollbar x-scrollable style="height: 100%">
          <div class="task-board">
            <draggable
              v-model="listData"
              item-key="statusItem"
              :style="{ display: 'flex', height: '100%' }"
              @change="dragChange"
              :move="moveList"
              :animation="200"
            >
              <template #item="{ element }">
                <kanban-board
                  ref="kanban"
                  @changeStatus="changeStatus($event, element)"
                  :taskData="element"
                  @showDetail="getDetail"
                  @createTask="createBaseTask(element)"
                  @select="selectTools($event, element)"
                  @toggleComplete="toggleComplete2($event)"
                ></kanban-board>
              </template>
            </draggable>
            <div class="create-stage">
              <div class="create-stage-title" @click="createStatusLink" v-show="showCreate">
                <a>
                  <n-icon size="14" class="add">
                    <Add />
                  </n-icon>
                  <div>新建任务状态</div>
                </a>
              </div>
              <div class="create-stage-body" v-show="!showCreate">
                <div>
                  <n-input
                    type="text"
                    placeholder="新建任务状态"
                    clearable
                    ref="inputInstRef"
                    v-model:value="statusValue"
                  />
                </div>
                <div class="submit-set">
                  <n-button type="error" ghost @click="cancelCreate">取消</n-button>
                  <n-button type="info" ghost @click="createStatus(statusValue)">保存</n-button>
                </div>
              </div>
            </div>
          </div>
        </n-scrollbar>
      </div>
      <!-- 甘特视图 -->
      <div v-else style="padding: 20px; height: 100%">
        <GanttView></GanttView>
      </div>
      <div>
        <n-modal v-model:show="showModal" class="modalBox" @after-leave="leaveModal">
          <n-card
            style="width: 1200px"
            title="任务详情"
            :bordered="false"
            size="huge"
            :segmented="{
              content: 'hard',
            }"
          >
            <template #header-extra>
              <div class="headMenu">
                <div title="返回">
                  <n-icon
                    size="24"
                    class="menuItem"
                    v-show="modalData.level > 1"
                    @click="jumpBack(modalData)"
                  >
                    <KeyboardReturnOutlined />
                  </n-icon>
                </div>
                <div title="编辑">
                  <n-icon
                    size="24"
                    class="menuItem"
                    @click="editTaskDetail"
                    v-show="showEditTaskDetailBtn"
                  >
                    <Edit24Regular />
                  </n-icon>
                </div>
                <div title="退出编辑">
                  <n-icon
                    size="24"
                    class="menuItem"
                    @click="editTaskDetail"
                    v-show="!showEditTaskDetailBtn"
                  >
                    <PlaylistAddCheckRound />
                  </n-icon>
                </div>
                <div title="菜单">
                  <n-dropdown
                    trigger="click"
                    :options="menuOptions"
                    size="large"
                    @select="handleSelect"
                  >
                    <n-icon class="menuItem" size="24">
                      <Dots />
                    </n-icon>
                  </n-dropdown>
                </div>
                <div title="关闭">
                  <a class="menuItem close" @click="closeModal">
                    <n-icon size="24">
                      <CloseOutline />
                    </n-icon>
                  </a>
                </div>
              </div>
            </template>
            <div class="task-wrap">
              <div class="task-content">
                <div class="content-wrap">
                  <div class="content-left">
                    <div class="panel">
                      <div class="task-title">
                        <n-input
                          v-model:value="taskName"
                          type="text"
                          ref="titleInputRef"
                          v-show="showTaskTitleInput"
                          @blur="showTitleInput"
                          class="title-input"
                        />
                        <div
                          class="title-text"
                          :class="{ editable: editStatus }"
                          v-show="!showTaskTitleInput"
                          @click="showTitleInput"
                        >
                          {{ modalData.detail.title }}
                        </div>
                      </div>
                      <div class="task-basic-attrs-view">
                        <div class="field-list">
                          <div class="field">
                            <div class="field-left">
                              <n-icon size="14" class="task-icon">
                                <CheckSquareOutlined />
                              </n-icon>
                              <span class="field-name">完成状态</span>
                            </div>
                            <div class="field-right" :class="{ editable: editStatus }">
                              <n-popselect
                                v-model:value="modalData.detail.status_id"
                                @update:value="statusChange"
                                :options="statusArray"
                                trigger="click"
                                :disabled="!editStatus"
                              >
                                {{
                                  statusArray.find(
                                    (item) => item.value === modalData.detail.status_id
                                  ).label
                                }}
                              </n-popselect>
                            </div>
                          </div>
                          <div class="field">
                            <div class="field-left">
                              <n-icon size="14" class="task-icon">
                                <CheckSquareOutlined />
                              </n-icon>
                              <span class="field-name">任务类型</span>
                            </div>
                            <div class="field-right">
                              <n-popselect
                                :value="modalData.detail.type"
                                :options="taskTypes"
                                trigger="click"
                                :disabled="true"
                              >
                                {{ task[modalData.detail.type] }}
                              </n-popselect>
                            </div>
                          </div>
                          <div class="field">
                            <div class="field-left">
                              <n-icon size="14" class="task-icon">
                                <CheckSquareOutlined />
                              </n-icon>
                              <span class="field-name">创建人</span>
                            </div>
                            <div class="field-right" style="cursor: default">
                              <span
                                ><userInfo :userInfo="modalData.detail.originator">
                                  <template #username>
                                    <span class="sub-content">{{
                                      modalData.detail.originator?.user_name
                                    }}</span>
                                  </template>
                                </userInfo></span
                              >
                            </div>
                          </div>
                          <div class="field" v-if="modalData.detail.type !== 'PERSON'">
                            <div class="field-left">
                              <n-icon size="14" class="task-icon">
                                <CheckSquareOutlined />
                              </n-icon>
                              <span class="field-name">责任人</span>
                            </div>
                            <div class="field-right" :class="{ editable: editStatus }">
                              <n-popover
                                trigger="manual"
                                placement="bottom"
                                :show="showPopoverExecutor"
                                @clickoutside="editStatus ? (showPopoverExecutor = false) : ''"
                                :disabled="
                                  !editStatus ||
                                  (modalData.detail.type === 'ORGANIZATION' &&
                                    modalData.detail.executor_type === 'GROUP')
                                "
                              >
                                <template #trigger>
                                  <div @click="editStatus ? (showPopoverExecutor = true) : ''">
                                    {{
                                      modalData.detail.executor
                                        ? modalData.detail.executor_type === 'PERSON'
                                          ? modalData.detail.type === 'GROUP'
                                            ? `${modalData.detail.executor_group?.name}/${modalData.detail.executor?.user_name}`
                                            : modalData.detail.executor?.user_name
                                          : `${modalData.detail.executor_group?.name}/${modalData.detail.executor?.user_name}`
                                        : '待认领'
                                    }}
                                  </div>
                                </template>
                                <taskMemberMenu
                                  :type="
                                    modalData.detail.type === 'ORGANIZATION' ||
                                    modalData.detail.type === 'VERSION'
                                      ? 'ALL'
                                      : 'PERSON'
                                  "
                                  :groupId="modalData.detail.group_id"
                                  @getPerson="getExecutors"
                                  :disabled="!editStatus"
                                  :defaultValue="modalData.detail.executor.user_name"
                                ></taskMemberMenu>
                              </n-popover>
                            </div>
                          </div>
                          <div class="field" v-if="modalData.detail.type !== 'PERSON'">
                            <div class="field-left">
                              <n-icon size="14" class="task-icon">
                                <CheckSquareOutlined />
                              </n-icon>
                              <span class="field-name">协助人</span>
                            </div>
                            <div class="field-right" :class="{ editable: editStatus }">
                              <n-popover
                                trigger="manual"
                                placement="bottom"
                                :disabled="!editStatus"
                                :show="showPopoverHelper"
                                @clickoutside="editStatus ? (showPopoverHelper = false) : ''"
                              >
                                <template #trigger>
                                  <div @click="editStatus ? (showPopoverHelper = true) : ''">
                                    <template
                                      v-if="
                                        Array.isArray(modalData.helper) && modalData.helper.length
                                      "
                                    >
                                      <span v-for="item in modalData.helper" :key="item.id">
                                        <userInfo :userInfo="item">
                                          <template #username>
                                            <span class="sub-content">{{
                                              item.name ? item.name : item.user_name
                                            }}</span>
                                          </template> </userInfo
                                        >&nbsp;&nbsp;
                                      </span>
                                    </template>
                                    <template v-else>
                                      {{ '无' }}
                                    </template>
                                  </div>
                                </template>
                                <taskMemberMenu
                                  @getPerson="getHelper"
                                  :multiple="true"
                                  :originator="modalData.detail.originator.user_id"
                                  :type="
                                    modalData.detail.type === 'ORGANIZATION' ||
                                    modalData.detail.type === 'VERSION'
                                      ? 'ALL'
                                      : 'PERSON'
                                  "
                                  :groupId="modalData.detail.group_id"
                                  :defaultValue="modalData.helper"
                                ></taskMemberMenu>
                              </n-popover>
                            </div>
                          </div>
                          <div class="field">
                            <div class="field-left">
                              <n-icon size="14" class="task-icon">
                                <CheckSquareOutlined />
                              </n-icon>
                              <span class="field-name">里程碑</span>
                            </div>
                            <div class="field-right" :class="{ editable: editStatus }">
                              <n-popover
                                trigger="manual"
                                placement="bottom"
                                :disabled="!editStatus"
                                :show="showMilepost"
                                @clickoutside="editStatus ? (showMilepost = false) : ''"
                              >
                                <template #trigger>
                                  <div @click="editStatus ? (showMilepost = true) : ''">
                                    <p v-if="modalData.detail.type === 'VERSION'">
                                      {{
                                        modalData.detail.milestones
                                          ? modalData.detail.milestones
                                              .map((item) => item.name)
                                              .join(',')
                                          : '无'
                                      }}
                                    </p>
                                    <p v-else>
                                      {{
                                        modalData.detail.milestones
                                          ? modalData.detail.milestones
                                              .map((item) => item.name)
                                              .join(',')
                                          : modalData.detail.milestone
                                          ? modalData.detail.milestone
                                          : '无'
                                      }}
                                    </p>
                                  </div>
                                </template>
                                <Milepost
                                  @getMilepost="getMilepost"
                                  @getMileposts="getMileposts"
                                  :defaultValue="modalData.detail.milestones || 0"
                                  :multiple="
                                    modalData.detail.type === 'VERSION' ||
                                    modalData.detail.milestones
                                  "
                                ></Milepost>
                              </n-popover>
                            </div>
                          </div>
                          <div class="field">
                            <div class="field-left">
                              <n-icon size="14" class="task-icon">
                                <CheckSquareOutlined />
                              </n-icon>
                              <span class="field-name">开始时间</span>
                            </div>
                            <div class="field-right">
                              <div
                                v-show="!showStartTime && modalData.detail.start_time"
                                :class="{ editable: editStatus }"
                                @click="
                                  editStatus ? (showStartTime = true) : (showStartTime = false)
                                "
                              >
                                {{ formatTime(modalData.detail.start_time, 'yyyy-MM-dd') }}
                              </div>
                              <div v-show="showStartTime || !modalData.detail.start_time">
                                <n-date-picker
                                  type="date"
                                  clearable
                                  :disabled="!editStatus"
                                  @blur="showStartTime = false"
                                  @update:value="updateStartTime"
                                />
                              </div>
                            </div>
                          </div>
                          <div class="field">
                            <div class="field-left">
                              <n-icon size="14" class="task-icon">
                                <CheckSquareOutlined />
                              </n-icon>
                              <span class="field-name">截止时间</span>
                            </div>
                            <div class="field-right">
                              <div
                                v-show="!showClosingTime && modalData.detail.deadline"
                                :class="{ editable: editStatus }"
                                @click="
                                  editStatus ? (showClosingTime = true) : (showClosingTime = false)
                                "
                              >
                                {{ formatTime(modalData.detail.deadline, 'yyyy-MM-dd') }}
                              </div>
                              <div v-show="showClosingTime || !modalData.detail.deadline">
                                <n-date-picker
                                  type="date"
                                  clearable
                                  :disabled="!editStatus"
                                  @blur="showClosingTime = false"
                                  @update:value="updateClosingTime"
                                />
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div class="content-right">
                    <div class="panel">
                      <div class="task-basic-attrs-view">
                        <div class="field-list">
                          <div class="field">
                            <div class="field-left">
                              <n-icon size="14" class="task-icon">
                                <CheckSquareOutlined />
                              </n-icon>
                              <span class="field-name">报告列表</span>
                            </div>
                          </div>
                          <div class="reportList">
                            <div
                              class="field-content"
                              v-for="(v, i) in modalData.reportArray"
                              :key="i"
                            >
                              <div class="task-name" @click="showReport(v)">
                                {{ v.title }}
                              </div>
                            </div>
                          </div>
                          <div class="field">
                            <div class="field-left">
                              <n-icon size="14" class="task-icon">
                                <CheckSquareOutlined />
                              </n-icon>
                              <span class="field-name">执行机架构</span>
                            </div>
                            <div class="field-right" :class="{ editable: editStatus }">
                              <n-popselect
                                v-model:value="modalData.detail.frame"
                                @update:value="frameChange"
                                :options="frameArray"
                                trigger="click"
                                :disabled="!editStatus || modalData.detail.is_manage_task"
                              >
                                <span
                                  :style="{
                                    color:
                                      !editStatus || modalData.detail.is_manage_task ? 'grey' : '',
                                  }"
                                >
                                  {{ modalData.detail.frame || '请选择' }}
                                </span>
                              </n-popselect>
                            </div>
                          </div>
                          <div class="field">
                            <div class="field-left">
                              <n-icon size="14" class="task-icon">
                                <CheckSquareOutlined />
                              </n-icon>
                              <span
                                class="field-name"
                                title="当关联子任务均'已完成'时,是否此任务自动完成"
                                >自动关联完成</span
                              >
                            </div>
                            <div class="field-right" :class="{ editable: editStatus }">
                              <n-popselect
                                v-model:value="modalData.detail.automatic_finish"
                                @update:value="autocompleteChange"
                                :options="autocompleteArray"
                                trigger="click"
                                :disabled="!editStatus"
                              >
                                {{ modalData.detail.automatic_finish ? '是' : '否' }}
                              </n-popselect>
                            </div>
                          </div>
                          <div class="field">
                            <div class="field-left">
                              <n-icon size="14" class="task-icon">
                                <CheckSquareOutlined />
                              </n-icon>
                              <span class="field-name">是否管理型任务</span>
                            </div>
                            <div class="field-right">
                              <span v-show="!editStatus">{{
                                modalData.detail.is_manage_task ? '是' : '否'
                              }}</span>
                              <n-checkbox
                                v-show="editStatus"
                                @update:checked="changeManage"
                                :checked="modalData.detail.is_manage_task"
                              ></n-checkbox>
                            </div>
                          </div>
                          <div class="field">
                            <div class="field-left">
                              <n-icon size="14" class="task-icon">
                                <CheckSquareOutlined />
                              </n-icon>
                              <span class="field-name">完成度</span>
                            </div>
                            <div class="field-right">
                              <span v-show="!editStatus">{{ modalData.detail.percentage }}</span>
                              <n-input-number
                                v-show="editStatus"
                                v-model:value="modalData.detail.percentage"
                                @blur="setTaskPercentage"
                                :min="0"
                                :max="100"
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="content-main">
                  <div class="field">
                    <div class="field-left">
                      <n-icon size="14" class="task-icon">
                        <CheckSquareOutlined />
                      </n-icon>
                      <span class="field-name">内容</span>
                    </div>
                    <div class="field-right">
                      <n-input
                        v-model:value="modalData.detail.content"
                        type="textarea"
                        style="min-width: 1000px; min-height: 30px"
                        ref="contentInputRef"
                        v-show="showContentInput"
                        @blur="showContent"
                        :autosize="{
                          minRows: 3,
                          maxRows: 8,
                        }"
                      />
                      <div
                        :class="{ editable: editStatus }"
                        v-show="!showContentInput"
                        @click="showContent"
                      >
                        <n-scrollbar style="max-height: 250px">
                          {{ modalData.detail.content || '无' }}
                        </n-scrollbar>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <template #footer>
              <n-card
                title=""
                :segmented="{
                  content: 'hard',
                  footer: 'hard',
                }"
                style=""
              >
                <template #header>
                  <div class="titleWrap">
                    <span
                      @click="toggleContent('comment')"
                      :class="{ active: showFooterContent == 'comment' }"
                      >评论</span
                    >
                    <span
                      @click="toggleContent('task')"
                      :class="{ active: showFooterContent == 'task' }"
                      >关联任务</span
                    >
                    <span
                      v-if="!modalData.detail.is_manage_task"
                      @click="toggleContent('case')"
                      :class="{ active: showFooterContent == 'case' }"
                      >关联用例</span
                    >
                  </div>
                </template>
                <div style="height: 300px" v-if="showFooterContent == 'comment'" class="log-wrap">
                  <n-scrollbar style="height: 100%">
                    <div v-for="(v, i) in modalData.comments" :key="i">
                      <div class="log-comment">
                        <div class="log-txt">
                          <div class="user">
                            <span><img :src="v.avatar_url" class="avatar" /></span>
                            <div class="name">{{ v.user_name }}</div>
                          </div>
                          <span class="time">{{
                            formatTime(v.create_time, 'yyyy-MM-dd hh:mm:ss')
                          }}</span>
                        </div>
                        <div class="log-txt">
                          <div class="m-t-xs" v-dompurify-html="v.content"></div>
                        </div>
                      </div>
                    </div>
                  </n-scrollbar>
                </div>
                <template #footer v-if="showFooterContent == 'comment'">
                  <div class="footer">
                    <div>
                      <editor
                        v-model="commentInput"
                        tag-name="div"
                        :init="init"
                        :api-key="apiKey"
                      />
                    </div>
                    <div class="commentBtn">
                      <n-button class="btn" type="info" @click="commentFn(commentInput)"
                        >评论</n-button
                      >
                    </div>
                  </div>
                </template>
                <div v-if="showFooterContent == 'case' && !modalData.detail.is_manage_task">
                  <div>
                    <div>
                      <div
                        class="associated-task"
                        style="display: inline-block"
                        @click="clickAssociatedCases"
                        v-show="editStatus"
                      >
                        <a>
                          <n-icon size="16" class="add">
                            <Add />
                          </n-icon>
                          <span>关联用例</span>
                        </a>
                      </div>
                      <div class="associated-task-body" v-show="showAssociatedCases">
                        <n-select
                          class="select"
                          placeholder="请选择里程碑"
                          v-model:value="associatedMilestone"
                          :options="associatedMilestoneOptions"
                          clearable
                        />
                        <div class="submit-set">
                          <n-button type="error" ghost @click="showAssociatedCases = false"
                            >取消</n-button
                          >
                          <n-button type="info" ghost @click="addCase(associatedMilestone)"
                            >关联</n-button
                          >
                        </div>
                      </div>
                    </div>
                    <div class="caseWrap">
                      <div class="header">关联的测试用例</div>
                      <n-data-table
                        remote
                        ref="useCaseTableView"
                        :loading="caseLoading"
                        :columns="caseViewColumns"
                        :data="casesData"
                        :single-line="false"
                      />
                    </div>
                  </div>
                </div>
                <div v-if="showFooterContent == 'task'">
                  <div>
                    <div
                      class="associated-task"
                      style="display: inline-block"
                      @click="associatedTask"
                      v-show="editStatus"
                    >
                      <a>
                        <n-icon size="16" class="add">
                          <Add />
                        </n-icon>
                        <span>关联父任务</span>
                      </a>
                    </div>
                    <div class="associated-task-body" v-show="!showAssociatedTask">
                      <n-select
                        class="select"
                        placeholder="请选择"
                        v-model:value="associatedTaskValue"
                        :options="fatherTaskArrayTemp"
                        filterable
                        :loading="fatherTaskLoading"
                        clearable
                        remote
                        @focus="handleFocusFatherTask"
                        @search="handleSearchFatherTask"
                      />
                      <div class="submit-set">
                        <n-button type="error" ghost @click="cancelAssociatedTask">取消</n-button>
                        <n-button type="info" ghost @click="associatedTaskBtn(associatedTaskValue)"
                          >关联</n-button
                        >
                      </div>
                    </div>
                  </div>
                  <div>
                    <div
                      class="associated-task"
                      style="display: inline-block"
                      @click="associatedChildTask"
                      v-show="editStatus"
                    >
                      <a>
                        <n-icon size="16" class="add">
                          <Add />
                        </n-icon>
                        <span>关联子任务</span>
                      </a>
                    </div>
                    <div class="associated-task-body" v-show="!showAssociatedChildTask">
                      <n-select
                        class="select"
                        placeholder="请选择"
                        v-model:value="associatedChildTaskValue"
                        :options="childTaskArrayTemp"
                        filterable
                        :loading="childTaskLoading"
                        clearable
                        remote
                        @focus="handleFocusChildTask"
                        @search="handleSearchChildTask"
                      />
                      <div class="submit-set">
                        <n-button type="error" ghost @click="cancelAssociatedChildTask"
                          >取消</n-button
                        >
                        <n-button
                          type="info"
                          ghost
                          @click="associatedChildTaskBtn(associatedChildTaskValue)"
                          >关联</n-button
                        >
                      </div>
                    </div>
                  </div>
                  <div style="margin-top: 20px">
                    <n-data-table
                      :columns="familyColumns"
                      :data="modalData.relationTask"
                      :row-props="familyRowProps"
                    />
                  </div>
                </div>
              </n-card>
            </template>
          </n-card>
        </n-modal>
      </div>
      <div>
        <n-modal v-model:show="showCaseModal">
          <n-card style="width: 600px" title="测试用例" :bordered="false" size="huge">
            <div style="display: flex; margin-bottom: 10px; align-items: center">
              <span class="label">测试套:</span>
              <n-select
                v-model:value="suiteId"
                filterable
                placeholder="请选择测试套"
                :options="suiteOptions"
                clearable
                remote
                @search="suiteHandleSearch"
              />
              <span class="label">用例名称:</span>
              <n-input placeholder="请输入要查询的用例名称" v-model:value="caseStr" />
              <n-button type="primary" @click="queryCase" style="margin-left: 10px">
                <template #icon>
                  <n-icon>
                    <ios-search />
                  </n-icon>
                </template>
                查询
              </n-button>
            </div>
            <n-data-table
              remote
              ref="useCaseTable"
              :columns="caseColumns"
              :data="caseData"
              :pagination="casePagination"
              :loading="loadingRef"
              :row-key="caseRowKey"
              @update:page="handleCasePageChange"
              v-model:checked-row-keys="checkedRowKeys"
            />
            <div class="btnWrap">
              <n-button type="error" ghost class="btn" @click="cancelCaseBtn">取消</n-button>
              <n-button type="info" ghost class="btn" @click="addCaseBtn">确定</n-button>
            </div>
          </n-card>
        </n-modal>
      </div>
      <div>
        <n-modal v-model:show="distributeCaseModal">
          <n-card style="width: 600px" title="分配测试用例" :bordered="false" size="huge">
            <div style="display: flex">
              <n-select
                placeholder="请选择子任务"
                style="width: 70%"
                v-model:value="distributeCaseTaskValue"
                :options="distributeCaseOption"
              />
              <div style="width: 30%; display: flex; justify-content: space-evenly">
                <n-button type="error" ghost @click="cancelDistributeCase">取消</n-button>
                <n-button type="info" ghost @click="distributeCaseBtn(distributeCaseTaskValue)"
                  >分配</n-button
                >
              </div>
            </div>
          </n-card>
        </n-modal>
        <n-modal v-model:show="distributeTaskModal">
          <n-spin :show="showDistributeTaskSpin">
            <template #description> 正在分配... </template>
            <n-card style="width: 600px" title="分配任务" :bordered="false" size="huge">
              <template #header-extra>
                <div>
                  <n-switch v-model:value="distributeAllCases">
                    <template #checked>全用例分配</template>
                    <template #unchecked>仅分配未完成</template>
                  </n-switch>
                </div>
              </template>
              <n-form :label-width="80">
                <n-form-item label="模板">
                  <n-select
                    placeholder="请选择模板"
                    v-model:value="distributeTaskValue"
                    :options="distributeTaskOption"
                  />
                </n-form-item>
                <n-form-item label="里程碑">
                  <n-select
                    placeholder="请选择里程碑"
                    v-model:value="distributeTaskMilestoneValue"
                    :options="distributeTaskMilestoneOption"
                  />
                </n-form-item>
              </n-form>
              <n-space>
                <n-button type="error" ghost @click="cancelDistributeTask">取消</n-button>
                <n-button type="info" ghost @click="distributeTaskBtn(distributeTaskValue)"
                  >分配</n-button
                >
              </n-space>
            </n-card>
          </n-spin>
        </n-modal>
      </div>
      <div>
        <n-modal v-model:show="showVersionTaskModal">
          <n-card style="width: 600px" title="创建版本任务" :bordered="false" size="huge">
            <n-form
              :model="modelVersion"
              :rules="rulesVersion"
              ref="formRefVersion"
              label-placement="left"
              :label-width="80"
              size="medium"
              :style="{}"
            >
              <n-form-item label="名称" path="title">
                <n-input placeholder="请输入任务名称" v-model:value="modelVersion.title" />
              </n-form-item>
              <n-form-item label="执行者" path="executor_id">
                <n-cascader
                  :value="modelVersion.executor_id"
                  placeholder="请选择"
                  :options="orgOptions"
                  :cascade="false"
                  check-strategy="child"
                  :show-path="true"
                  remote
                  @update:value="versionSelect"
                  :on-load="handleLoad"
                />
              </n-form-item>
              <n-form-item label="里程碑" path="milestone_id">
                <n-select
                  v-model:value="modelVersion.milestone_id"
                  placeholder="请选择里程碑"
                  :options="milestoneOptions"
                  filterable
                  clearable
                />
              </n-form-item>
              <n-form-item label="开始日期" path="start_time">
                <n-date-picker type="date" v-model:value="modelVersion.start_time" />
              </n-form-item>
              <n-form-item label="截止日期" path="deadline">
                <n-date-picker type="date" v-model:value="modelVersion.deadline" />
              </n-form-item>
              <n-form-item label="关键词" path="keywords">
                <n-input
                  placeholder="请输入关键词"
                  v-model:value="modelVersion.keywords"
                  type="textarea"
                />
              </n-form-item>
              <n-form-item label="摘要" path="abstract">
                <n-input
                  placeholder="请输入报告摘要"
                  v-model:value="modelVersion.abstract"
                  type="textarea"
                />
              </n-form-item>
              <n-form-item label="缩略语清单" path="abbreviation">
                <n-input
                  placeholder="请输入缩略语清单"
                  v-model:value="modelVersion.abbreviation"
                  type="textarea"
                />
              </n-form-item>
              <div class="createButtonBox">
                <n-button class="btn" type="error" ghost @click="cancelCreateVersionTask"
                  >取消</n-button
                >
                <n-button class="btn" type="info" ghost @click="createVersionTaskBtn"
                  >创建</n-button
                >
              </div>
            </n-form>
          </n-card>
        </n-modal>
      </div>
      <div>
        <CaseIssueModal
          :caseIssueModalData="caseIssueModalData"
          :taskDetailData="modalData"
          ref="caseIssueModalRef"
        ></CaseIssueModal>
      </div>
      <!-- 生成报告 -->
      <div>
        <n-modal
          v-model:show="showReportModal"
          preset="dialog"
          :show-icon="false"
          title="Dialog"
          class="previewWindow"
          :style="{ width: previewWidth + 'px', height: previewHeight + 'px' }"
        >
          <template #header>
            <h3>{{ md.name }}</h3>
          </template>
          <div class="previewContent" :style="{ height: previewHeight - 100 + 'px' }">
            <v-md-editor
              v-model="md.content"
              :left-toolbar="tools"
              :right-toolbar="rightTools"
              :include-level="[1, 4]"
              :toolbar="toolbar"
              @save="saveFile"
            ></v-md-editor>
          </div>
        </n-modal>
      </div>
      <div>
        <n-modal v-model:show="resultCaseModal" class="modalBox">
          <n-card
            style="width: 900px"
            :bordered="false"
            size="medium"
            :title="resultCaseModalData.name"
          >
            <template #header-extra>
              <div class="headMenu">
                <div title="编辑">
                  <n-icon
                    size="24"
                    class="menuItem"
                    @click="editResultCase"
                    v-show="!editResultFileds"
                  >
                    <Edit24Regular />
                  </n-icon>
                </div>

                <div title="退出编辑">
                  <n-icon
                    size="24"
                    class="menuItem"
                    @click="editResultCase"
                    v-show="editResultFileds"
                  >
                    <PlaylistAddCheckRound />
                  </n-icon>
                </div>

                <div title="关闭">
                  <a class="menuItem close" @click="closeResultModal">
                    <n-icon size="24">
                      <CloseOutline />
                    </n-icon>
                  </a>
                </div>
              </div>
            </template>

            <n-form
              :model="modelResult"
              :rules="rulesResult"
              ref="formRefResult"
              label-placement="left"
              :label-width="100"
              size="medium"
              :style="{}"
              :disabled="!editResultFileds"
            >
              <n-grid :cols="18" :x-gap="24">
                <n-form-item-gi :span="18" label="执行时长：" path="running_time">
                  <div style="line-height: 34px">{{ modelResult.running_time }}</div>
                </n-form-item-gi>
                <n-form-item-gi :span="9" label="执行结果：" path="result">
                  <n-select
                    placeholder="执行结果"
                    :options="resultCaseoptions"
                    @update:value="updateResult"
                    v-model:value="modelResult.result"
                  />
                </n-form-item-gi>

                <n-form-item-gi
                  :span="18"
                  size="large"
                  label="详细信息"
                  label-placement="top"
                  label-style="color:#1890ff"
                >
                  <hr style="border: 1px solid #eeebeb; width: 100%" />
                </n-form-item-gi>

                <n-form-item-gi :span="9" label="结果日志连接" path="log_url">
                  <n-input placeholder="请输入结果日志连接" v-model:value="modelResult.log_url" />
                </n-form-item-gi>

                <n-form-item-gi :span="9" label="错误类型" path="fail_type">
                  <n-input placeholder="请输入错误类型" v-model:value="modelResult.fail_type" />
                </n-form-item-gi>
                <n-form-item-gi :span="24" label="错误详情" path="details">
                  <editor
                    id="tinymce"
                    v-model="modelResult.details"
                    tag-name="div"
                    :init="init"
                    :disabled="!editResultFileds"
                    :api-key="apiKey"
                  />
                </n-form-item-gi>
              </n-grid>
            </n-form>
            <div style="display: flex; justify-content: right; margin: 20px 20px 0 0">
              <n-button type="info" ghost @click="handleEditResultCase">确定</n-button>
            </div>
          </n-card>
        </n-modal>
      </div>
    </div>
  </n-spin>
</template>

<script>
import { defineComponent, getCurrentInstance } from 'vue';
import KanbanBoard from '@/components/tm/KanbanBoard.vue';
import draggable from 'vuedraggable';
import { Add, CloseOutline } from '@vicons/ionicons5';
import { CheckSquareOutlined } from '@vicons/antd';
import { Dots } from '@vicons/tabler';
import { KeyboardReturnOutlined, PlaylistAddCheckRound } from '@vicons/material';
import { Edit24Regular } from '@vicons/fluent';
import taskMemberMenu from '@/components/tm/taskMemberMenu.vue';
import Milepost from '@/components/tm/Milepost.vue';
import { IosSearch } from '@vicons/ionicons4';
import { modules } from './modules/index';
import Editor from '@tinymce/tinymce-vue';
import CaseIssueModal from './CaseIssueModal.vue';
import { workspace } from '@/assets/config/menu.js';
import { storage } from '@/assets/utils/storageUtils';

export default defineComponent({
  components: {
    KanbanBoard,
    draggable,
    Add,
    CheckSquareOutlined,
    Dots,
    CloseOutline,
    KeyboardReturnOutlined,
    taskMemberMenu,
    Milepost,
    IosSearch,
    Edit24Regular,
    PlaylistAddCheckRound,
    editor: Editor,
    CaseIssueModal,
  },
  setup() {
    const { proxy } = getCurrentInstance();
    let listDataTemp;
    modules.initData();
    modules.getGroup();
    modules.getRelationTask();
    modules.getFrame();
    modules.tinymce.init;
    document.addEventListener('searchTask', (e) => {
      modules.showLoading.value = true;
      const temp = JSON.parse(JSON.stringify(e.detail));
      if (temp.status_id) {
        listDataTemp = modules.listData.value;
        modules.listData.value = modules.listData.value.filter((item) => {
          return item.id === temp.status_id;
        });
      } else {
        modules.listData.value = listDataTemp ? listDataTemp : modules.listData.value;
      }
      if (temp.participant_id?.length) {
        temp.participant_id = temp.participant_id.join(',');
      }
      if (temp.milestone_id?.length) {
        temp.milestone_id = temp.milestone_id.join(',');
      }
      const allRequest = modules.listData.value.map((item) => {
        return proxy.$axios.get(`/v1/ws/${workspace.value}/tasks`, {
          ...temp,
          status_id: item.id,
          org_id: storage.getLocalValue('unLoginOrgId')?.id,
        });
      });
      Promise.allSettled(allRequest)
        .then((results) => {
          modules.showLoading.value = false;
          results.forEach((item, index) => {
            modules.listData.value[index].tasks = [];
            if (item?.value?.data?.items?.length) {
              modules.listData.value[index].tasks = item.value.data.items;
            }
            proxy.$refs.kanban.showTaskList = true;
          });
        })
        .catch(() => {
          modules.showLoading.value = false;
        });
    });
    return {
      ...modules,
    };
  },
});
</script>

<style lang="less" scoped>
@font-face {
  font-family: 'iconfont'; /* Project id  */
  src: url('iconfont.ttf?t=1637235844418') format('truetype');
}

:deep(.n-spin-content) {
  height: 100%;
}

:deep(.n-scrollbar-content) {
  height: 100%;
}
.iconfont {
  font-family: 'iconfont' !important;
  font-size: 20px !important;
  font-style: normal;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.icon-download:before {
  content: '\e74d';
}
.label {
  margin: 0 5px;
  flex-shrink: 0;
}
.createButtonBox {
  display: flex;
  justify-content: space-evenly;
  .btn {
    width: 100px;
  }
  .versionTask {
    width: 228px;
  }
}

.task-body {
  height: 100%;
  .task-board {
    position: relative;
    padding: 20px;
    height: 100%;
    max-height: 900px;
    display: flex;
    justify-content: flex-start;

    .create-stage {
      height: auto;
      width: 245px;
      vertical-align: middle;
      border-radius: 3px;
      padding: 14px 14px;
      font-size: 14px;
      font-weight: 700;
      z-index: 1;

      .create-stage-title {
        height: 25px;
        cursor: pointer;

        a {
          color: rgba(0, 0, 0, 0.45);
          display: flex;
          align-items: center;

          &:hover {
            color: #3da8f5;
          }
          .add {
            vertical-align: middle;
          }
          div {
            margin-left: 5px;
          }
        }
      }

      .create-stage-body {
        .submit-set {
          padding-top: 10px;
          display: flex;
          justify-content: space-evenly;
        }
      }
    }
  }
}

.modalBox {
  .headMenu {
    width: auto;
    display: flex;
    justify-content: space-between;

    .menuItem {
      margin: 0 5px;
      cursor: pointer;
    }

    .close {
      cursor: pointer;
    }
  }

  .task-wrap {
    .task-content {
      .content-wrap {
        display: flex;
        justify-content: flex-start;

        .content-left {
          overflow: hidden;
          // height: 1000px;
          // border-right: 1px solid #e5e5e5;
          min-width: 590px;
          flex: 1;
        }

        .panel {
          position: relative;
          box-sizing: border-box;
          height: 100%;
          overflow: hidden;
          margin-right: -17px;

          .task-title {
            margin: 10px 40px 20px 20px;
            cursor: text;

            .title-input {
              font-size: 20px;
              padding: 8px;
              border-radius: 4px;
              width: 100%;
            }

            .title-text {
              font-size: 20px;
              // padding: 8px;
              border-radius: 4px;
              height: 50px;
              display: flex;
              align-items: center;
              margin-left: 20px;
            }
          }

          .task-basic-attrs-view {
            color: rgba(0, 0, 0, 0.45);

            .field-list {
              padding: 0 40px 0 32px;

              .field {
                display: flex;
                justify-content: flex-start;
                align-items: center;
                margin: 12px 0;
                min-height: 36px;

                .field-left {
                  width: 132px;
                  padding-right: 12px;

                  .task-icon {
                    vertical-align: middle;
                  }

                  .field-name {
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    padding-left: 8px;
                    cursor: default;
                  }
                }

                .field-right {
                  cursor: pointer;
                  min-width: 100px;
                  max-width: calc(100% - 132px);
                }

                .block-field {
                  width: 100%;
                  border: 1px solid #e5e5e5;
                  border-radius: 4px;
                  padding: 2px 0;
                  margin-bottom: 12px;
                  display: flex;
                  justify-content: flex-start;
                  flex-direction: row;
                }
              }
            }
          }
        }

        .content-right {
          width: 410px;
        }
      }

      .content-main {
        .field {
          display: flex;
          justify-content: flex-start;
          align-items: center;
          color: rgba(0, 0, 0, 0.45);
          min-height: 36px;
          margin-left: 30px;

          .field-left {
            display: flex;
            align-items: center;
            width: 132px;
            padding-right: 12px;

            .task-icon {
              vertical-align: middle;
            }

            .field-name {
              overflow: hidden;
              text-overflow: ellipsis;
              white-space: nowrap;
              padding-left: 8px;
              cursor: default;
            }
          }

          .field-right {
            cursor: pointer;
            // min-width: 100px;
            // max-width: calc(100% - 132px);
          }
        }
      }
    }
  }

  .log-wrap {
    .log-comment {
      // max-width: 405px;
      align-items: end;
      margin-bottom: 15px;

      .log-txt {
        display: flex;
        justify-content: space-between;
        color: #333;

        .user {
          display: flex;
          align-items: center;

          .avatar {
            opacity: 1;
            flex: 0 0 auto;
            background-size: cover !important;
            background-repeat: no-repeat !important;
            background-position: 50% !important;
            border-radius: 50%;
            display: inline-block;
            background-color: #eee;
            width: 24px;
            height: 24px;
            vertical-align: middle;
            border-style: none;
          }

          .name {
            margin-left: 10px;
          }
        }

        .time {
          margin-right: 10px;
        }

        .m-t-xs {
          padding: 0px 10px 0px 30px;
          color: #333;
          width: 100%;
          box-sizing: border-box;
          word-wrap: break-word;
        }
      }
    }
  }

  .caseWrap {
    border: 1px solid #e5e5e5;
    border-radius: 4px;
    margin-top: 10px;

    .coll {
      padding: 0 16px;
      width: auto;
    }
    .header {
      padding-left: 16px;
      height: 40px;
      line-height: 40px;
      color: #8c8c8c;
    }

    li {
      display: flex;
      margin-left: 25px;
    }
  }

  .footer {
    .commentBtn {
      display: flex;
      justify-content: flex-end;
      margin-top: 10px;
    }
  }
}

.titleWrap {
  display: flex;

  span {
    margin: 0 10px;
    cursor: pointer;
    &:hover {
      color: #3da8f5;
    }
  }
  .active {
    border-bottom: 3px solid #3da8f5;
  }
}
.btnWrap {
  display: flex;
  justify-content: center;
  margin-top: 20px;
  .btn {
    margin: 0 10px;
  }
}
.associated-task {
  height: 25px;
  cursor: pointer;
  a {
    color: #1890ff;
    display: flex;
    align-items: center;
    align-items: center;

    .add {
      vertical-align: middle;
    }
    div {
      margin-left: 5px;
    }
  }
}
.associated-task-body {
  display: flex;
  vertical-align: middle;

  .select {
    width: 40%;
  }
  .submit-set {
    display: flex;
    justify-content: space-evenly;
    width: 150px;
  }
}
.has-associated-task,
.reportList {
  .field-title {
    font-weight: bold;
    color: #1f2225;
  }
  .field-content {
    display: flex;
    vertical-align: middle;
    justify-content: flex-start;
    margin-left: 16px;
    .task-name {
      width: 300px;
      overflow: hidden;
      cursor: pointer;
      line-height: 27px;
      &:hover {
        background: rgb(233, 233, 233);
      }
    }
  }
}
.previewContent {
  overflow-y: auto;
}

.editable {
  color: #1890ff;
}
</style>
<style>
.modalBox {
  .n-form-item .n-form-item-blank {
    display: block !important;
  }
}
</style>
