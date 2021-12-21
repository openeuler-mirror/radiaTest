import axios from '@/axios';

const getProductOpts = (productOpts, loading) => {
  loading ? loading.value = true : 0;
  productOpts.value = [];
  axios
    .get('/v1/product')
    .then((res) => {
      loading ? loading.value = false : 0;
      res.forEach((item) => {
        if (!productOpts.value.includes(item.name)) {
          productOpts.value.push(item.name);
        }
      });
      productOpts.value = productOpts.value.map((name) => {
        return {
          label: name,
          value: name,
        };
      });
    })
    .catch(() => {
      loading ? loading.value = false : 0;
      window.$message?.error('无法连接服务器，获取产品选项失败');
    });
};

const getVersionOpts = (versionOpts, productName, loading) => {
  loading ? loading.value = true : 0;
  versionOpts.value = [];
  axios
    .get('/v1/product', { name: productName })
    .then((res) => {
      loading ? loading.value = false : 0;
      versionOpts.value = res.map((item) => {
        return {
          label: item.version,
          value: item.id.toString(),
        };
      });
    })
    .catch(() => {
      loading ? loading.value = false : 0;
      window.$message?.error('无法连接服务器，获取版本选项失败');
    });
};

const getMilestoneOpts = (milestoneOpts, productId, loading) => {
  loading ? loading.value = true : 0;
  milestoneOpts.value = [];
  axios
    .get('/v1/milestone/preciseget', {
      product_id: productId,
    })
    .then((res) => {
      loading ? loading.value = false : 0;
      res.forEach((item) => {
        milestoneOpts.value.push({
          label: item.name,
          value: item.id.toString(),
        });
      });
    })
    .catch(() => {
      loading ? loading.value = false : 0;
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
  loading ? loading.value = true : 0;
  axios
    .get(route, {
      milestone_id: milestoneId
    })
    .then((res) => {
      loading ? loading.value = false : 0;
      frameOpts.value = res.map((item) => {
        return {
          label: item.frame,
          value: item.frame,
        };
      });
    })
    .catch(() => {
      loading ? loading.value = false : 0;
      window.$message?.error('无法连接服务器，获取架构选项失败');
    });
};

export {
  getProductOpts,
  getVersionOpts,
  getMilestoneOpts,
  getFrameOpts,
};
