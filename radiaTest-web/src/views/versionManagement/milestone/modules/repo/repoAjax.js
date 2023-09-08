import axios from '@/axios';
import repoCard from './repoCard.js';
import milestoneTable from '@/views/versionManagement/milestone/modules/milestoneTable';

const getcode = (id, thisFrame) => {
  repoCard.loading.value = true;
  axios
    .get('/v1/repo', { milestone_id: id, frame: thisFrame })
    .then((res) => {
      const [data] = res.data;
      repoCard.repo.value[thisFrame] = data;
      repoCard.loading.value = false;
    })
    .catch((err) => {
      window.$message?.error(err);
      repoCard.loading.value = false;
    });
};

const handleCreateClick = (id, thisFrame) => {
  axios
    .post('/v1/repo', {
      milestone_id: id,
      frame: thisFrame,
      content: repoCard.content.value[thisFrame],
    })
    .then((res) => {
      if (res.error_code === '2000') {
        window.$message?.success('创建成功');
      } else {
        window.$message?.error('创建失败');
      }
      getcode(id, thisFrame);
      milestoneTable.getTableData();
    })
    .catch((err) => {
      window.$message?.error(
        `创建失败: + ${err.data.validation_error.body_params[0].msg}`
      );
    });
};
const handleEditClick = (frame) => {
  repoCard.edit.value[frame] = !repoCard.edit.value[frame];
  repoCard.content.value[frame] = repoCard.repo.value[frame].content;
};
const handleEditSubmit = (id, thisFrame) => {
  axios
    .put('/v1/repo', {
      id: repoCard.repo.value[thisFrame].id,
      milestone_id: id,
      frame: thisFrame,
      content: repoCard.content.value[thisFrame],
    })
    .then((res) => {
      if (res.error_code === '2000') {
        window.$message?.success('修改成功');
      } else {
        window.$message?.error('修改失败');
      }
      repoCard.edit.value[thisFrame] = false;
      getcode(id, thisFrame);
    })
    .catch((err) => {
      window.$message?.error(
        `创建失败: + ${err.data.validation_error.body_params[0].msg}`
      );
    });
};

export default {
  getcode,
  handleCreateClick,
  handleEditClick,
  handleEditSubmit,
};
