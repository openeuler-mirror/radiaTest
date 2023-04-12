import axios from '@/axios';
import { getRepo, getSuite, getPm, getVm } from '@/api/get';
import { workspace } from '@/assets/config/menu.js';

export async function createRepoOptions(filter) {
  const data = await getRepo(filter);
  return data.data.map((item) => ({
    label: item.git_url,
    value: String(item.id)
  }));
}
export async function createSuiteOptions(filter) {
  const data = await getSuite(filter);
  return data.data.map((item) => ({
    label: item.name,
    value: String(item.id),
    machineCount: item.machine_num,
    machineType: item.machine_type
  }));
}
export async function createCaseOptions(filter) {
  const res = await axios.get(`v1/ws/${workspace.value}/case/preciseget`, filter);
  return res?.data.map((v) => ({ label: v.name, value: v.id }));
}

export async function createPmOptions(filter) {
  const data = await getPm(filter);
  return data.data.map((item) => ({
    label: item.ip,
    value: String(item.id)
  }));
}
export async function createVmOptions(filter) {
  const data = await getVm(filter);
  return data.data.map((item) => ({
    label: item.ip,
    value: String(item.id)
  }));
}

const getProductOpts = (productOpts, loading) => {
  loading ? (loading.value = true) : 0;
  productOpts.value = [];
  axios
    .get(`/v1/ws/${workspace.value}/product`, { paged: false })
    .then((res) => {
      loading ? (loading.value = false) : 0;
      res.data.items.forEach((item) => {
        if (!productOpts.value.includes(item.name)) {
          productOpts.value.push(item.name);
        }
      });
      productOpts.value = productOpts.value.map((name) => {
        return {
          label: name,
          value: name
        };
      });
    })
    .catch(() => {
      loading ? (loading.value = false) : 0;
      window.$message?.error('无法连接服务器，获取产品选项失败');
    });
};

const getProductVersionOpts = (productOpts, loading) => {
  loading ? (loading.value = true) : 0;
  productOpts.value = [];
  axios
    .get(`/v1/ws/${workspace.value}/product`, { paged: false })
    .then((res) => {
      loading ? (loading.value = false) : 0;
      productOpts.value = res.data.items.map((item) => {
        return {
          label: `${item.name} ${item.version}`,
          value: item.id.toString()
        };
      });
    })
    .catch(() => {
      loading ? (loading.value = false) : 0;
      window.$message?.error('无法连接服务器，获取产品选项失败');
    });
};

const getProductVersionOrgOpts = (productOpts, loading) => {
  loading ? (loading.value = true) : 0;
  productOpts.value = [];
  axios
    .get(`/v1/ws/${workspace.value}/product`, { paged: false, permission_type: 'org' })
    .then((res) => {
      loading ? (loading.value = false) : 0;
      productOpts.value = res.data?.items?.map((item) => {
        return {
          label: `${item.name} ${item.version}`,
          value: item.id.toString()
        };
      });
    })
    .catch(() => {
      loading ? (loading.value = false) : 0;
      window.$message?.error('无法连接服务器，获取产品选项失败');
    });
};

const getCheckItemOpts = (checkItemOpts, loading) => {
  return new Promise((resolve) => {
    loading ? (loading.value = true) : 0;
    checkItemOpts.value = [];
    axios
      .get('/v1/checkitem', { page_num: 1, page_size: 999999 })
      .then((res) => {
        loading ? (loading.value = false) : 0;
        checkItemOpts.value = res.data.items.map((item) => {
          return {
            label: item.title,
            value: item.id
          };
        });
        resolve();
      })
      .catch(() => {
        loading ? (loading.value = false) : 0;
        window.$message?.error('无法连接服务器，获取检查项选项失败');
      });
  });
};

const getVersionOpts = (versionOpts, productName, loading) => {
  loading ? (loading.value = true) : 0;
  versionOpts.value = [];
  axios
    .get(`/v1/ws/${workspace.value}/product/preciseget`, { name: productName })
    .then((res) => {
      loading ? (loading.value = false) : 0;
      versionOpts.value = res.data.map((item) => {
        return {
          label: item.version,
          value: item.id.toString()
        };
      });
    })
    .catch(() => {
      loading ? (loading.value = false) : 0;
      window.$message?.error('无法连接服务器，获取版本选项失败');
    });
};

const getMilestoneOpts = (milestoneOpts, productId, loading) => {
  loading ? (loading.value = true) : 0;
  milestoneOpts.value = [];
  axios
    .get('/v1/milestone/preciseget', {
      product_id: productId
    })
    .then((res) => {
      loading ? (loading.value = false) : 0;
      res.data.forEach((item) => {
        milestoneOpts.value.push({
          label: item.name,
          value: item.id.toString()
        });
      });
    })
    .catch(() => {
      loading ? (loading.value = false) : 0;
      window.message?.error('无法连接服务器，获取里程碑选项失败');
    });
};

const getFrameOpts = (frameOpts, milestoneId, filetype, loading) => {
  let route;
  if (filetype === 'iso') {
    route = '/v1/imirroring/preciseget';
  } else {
    route = '/v1/qmirroring/preciseget';
  }
  loading ? (loading.value = true) : 0;
  axios
    .get(route, {
      milestone_id: milestoneId
    })
    .then((res) => {
      loading ? (loading.value = false) : 0;
      frameOpts.value = res.data.map((item) => {
        return {
          label: item.frame,
          value: item.frame
        };
      });
    })
    .catch(() => {
      loading ? (loading.value = false) : 0;
      window.$message?.error('无法连接服务器，获取架构选项失败');
    });
};

export {
  getProductOpts,
  getProductVersionOpts,
  getProductVersionOrgOpts,
  getVersionOpts,
  getMilestoneOpts,
  getFrameOpts,
  getCheckItemOpts
};
