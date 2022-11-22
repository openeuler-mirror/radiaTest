import { getAttachmentList, downloadAttachment } from '@/api/get';
import { addAttachment } from '@/api/post';
import { deleteRequireAttachment } from '@/api/delete';

const fileList = ref({
  statement: [],
  progress: [],
  validation: [],
});

function getFileList(id, _type) {
  getAttachmentList(id, { 'type': _type })
    .then((res) => {
      fileList.value[_type] = res.data.map(
        (_item) => {
          return {
            name: _item,
            status: 'finished',
          };
        }
      );
    });
}

const attachmentUploadRequest = (id, _type, { file, onProgress, onFinish, onError }) => {
  const formData = new FormData();
  formData.append('file', file.file);
  formData.append('type', _type);
  addAttachment(id, formData, onProgress)
    .then((res) => {
      if (res.status !== 200) {
        throw(res.statusText);
      } else if (res.json.error_code !== '2000') {
        throw(res.json.error_msg);
      }

      window.$message?.success('上传成功');
      getFileList(id, _type);
      onFinish();
    })
    .catch((err) => {
      window.$message?.error(`上传失败, ${err}`);
      onError();
    });
};

function handleUploadChange(_type, data) {
  fileList.value[_type] = data.fileList;
}

function handleRemove(id, _type, data) {
  if (data.file.status === 'finished') {
    return new Promise((resolve) => {
      deleteRequireAttachment(id, { type: _type, filename: data.file.name })
        .then(() => {
          resolve(true);
        })
        .catch(() => {
          resolve(false);
        });
    });
  }
  return null;
}

function handleDownload(id, _type, file) {
  downloadAttachment(id, { type: _type, filename: file.name })
    .then((res) => {
      const blob = new Blob([res]);
      const link = document.createElement('a');
      link.download = file.name;
      link.style.display = 'none';
      link.href = URL.createObjectURL(blob);
      document.body.appendChild(link);
      link.click();
      URL.revokeObjectURL(link.href);
      document.body.removeChild(link);
      window.$message?.info(`${file.name}已成功下载`);
    })
    .catch(() => {
      window.$message?.error(`${file.name}下载失败`);
    });
}

function cleanAttachmentList() {
  fileList.value = {
    statement: [],
    progress: [],
    validation: [],
  };
}

export {
  fileList,
  getFileList,
  handleRemove,
  handleUploadChange,
  attachmentUploadRequest,
  handleDownload,
  cleanAttachmentList,
};
