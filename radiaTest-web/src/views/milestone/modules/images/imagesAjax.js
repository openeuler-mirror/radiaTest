import axios from '@/axios';

const devideIsoData = (res, data) => {
  const aarch64 = res.find((item) => item.frame === 'aarch64');
  const x64 = res.find((item) => item.frame === 'x86_64');
  if (aarch64) {
    data.value.iso.aarch64.id = aarch64.id;
    data.value.iso.aarch64.url = aarch64.url;
    data.value.iso.aarch64.efi = aarch64.efi;
    data.value.iso.aarch64.ks = aarch64.ks;
    data.value.iso.aarch64.location = aarch64.location;
  }
  if (x64) {
    data.value.iso.x64.id = x64.id;
    data.value.iso.x64.url = x64.url;
    data.value.iso.x64.efi = x64.efi;
    data.value.iso.x64.ks = x64.ks;
    data.value.iso.x64.location = x64.location;
  }
};

const devideQcow2Data = (res, data) => {
  const aarch64 = res.find((item) => item.frame === 'aarch64');
  const x64 = res.find((item) => item.frame === 'x86_64');
  if (aarch64) {
    data.value.qcow2.aarch64.id = aarch64.id;
    data.value.qcow2.aarch64.url = aarch64.url;
    data.value.qcow2.aarch64.user = aarch64.user;
    data.value.qcow2.aarch64.port = aarch64.port;
    data.value.qcow2.aarch64.password = aarch64.password;
  }
  if (x64) {
    data.value.qcow2.x64.id = x64.id;
    data.value.qcow2.x64.url = x64.url;
    data.value.qcow2.x64.user = x64.user;
    data.value.qcow2.x64.port = x64.port;
    data.value.qcow2.x64.password = x64.password;
  }
};

const getIsoData = (form, data) => {
  axios
    .get('/v1/imirroring/preciseget', {
      milestone_id: form.value.id,
    })
    .then((res) => {
      if (res.data.length) {
        devideIsoData(res.data, data);
      }

    });
};

const getQcow2Data = (form, data) => {
  axios
    .get('/v1/qmirroring/preciseget', {
      milestone_id: form.value.id,
    })
    .then((res) => {
      if (res.data.length) {
        devideQcow2Data(res.data, data);
      }
    });
};

const getData = (form, data) => {
  getIsoData(form, data);
  getQcow2Data(form, data);
};

export {
  devideIsoData,
  devideQcow2Data,
  getData,
};

