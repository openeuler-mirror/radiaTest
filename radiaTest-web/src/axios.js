import axios from 'axios';
import { storage } from './assets/utils/storageUtils';
import router from './router';

//url接口头定义
const server = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json;charset=UTF-8',
  },
});


function getValueByKey(data, key) {
  if (!data) {
    return undefined;
  }
  if (data.get) {
    return data.get(key) === 'undefined' ? undefined : data.get(key);
  }
  return data[key];
}
//请求拦截器
server.interceptors.request.use(
  (config) => {
    let token;
    let keys;
    if (config.data?.entries) {
      keys = [];
      config.data.forEach((i, key) => {
        keys.push(key);
      });
    } else {
      keys = Object.keys(config.data || {});
    }
    for (const key of keys) {
      if (
        getValueByKey(config.data, key) === undefined ||
        getValueByKey(config.data, key) === null
      ) {
        if (config.data?.delete) {
          config.data?.delete(key);
        } else {
          delete config.data[key];
        }
      }
    }
    if (config.url.indexOf('login') === -1) {
      try {
        token = storage.getValue('token');
        if (token) {
          config.headers.Authorization = `JWT ${token}`;
        }
      } catch {
        token = '';
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);
//回应拦截器
server.interceptors.response.use(
  (response) => {
    if (
      response.data.error_code === 200 ||
      response.data.error_code === '2000' ||
      !response.data.error_code
    ) {
      response.headers.authorization && storage.setValue('token', response.headers.authorization);
      return Promise.resolve(response);
    }
    if (response.data.error_code === '4021') {
      router.replace(`/blank?redirect=${router.currentRoute.value.fullPath}`);
      return Promise.reject(response);
    }

    return Promise.reject(response);
  },
  (error) => {
    if (error.response?.status === 401) {
      window.$message?.destroyAll();
      window.sessionStorage.clear();
      error.response.data = {
        error_msg: '登录失效',
      };
      window.$message?.info(
        '请点击右上角登录按钮进行重新登录',
        {
          closable: true,
          duration: 10000
        }
      );
      if (router.currentRoute.value.matched[0].name === 'PersonalCenter') {
        router.replace({
          name: 'task'
        });
      } else {
        router.replace(`/blank?redirect=${router.currentRoute.value.fullPath}`);
      }
    } else if (error.response?.status === 500) {
      window.$message?.destroyAll();
      error.response.data = {
        error_msg: '服务端错误',
      };
    } else if (error.response?.status === 400) {
      const msg = error.response.data.validation_error.body_params
        ? error.response.data.validation_error.body_params[0].msg
        : error.response.data.validation_error.query_params[0]?.msg;

      error.response.data = {
        error_msg: msg,
      };
    }
    return Promise.reject(error.response || error);
  }
);

server.spread = axios.spread;
//方法定义
export default {
  server,
  post(url, data, config) {
    return new Promise((resolve, reject) => {
      server({
        method: 'post',
        url,
        data,
        ...config,
      })
        .then((res) => {
          resolve(res.data);
        })
        .catch((err) => {
          reject(err);
        });
    });
  },

  get(url, data, config) {
    return new Promise((resolve, reject) => {
      server({
        method: 'get',
        url,
        params: data,
        ...config,
      })
        .then((res) => {
          resolve(res.data);
        })
        .catch((err) => {
          reject(err);
        });
    });
  },

  put(url, data, config) {
    return new Promise((resolve, reject) => {
      server({
        method: 'put',
        url,
        data,
        ...config,
      })
        .then((res) => {
          resolve(res.data);
        })
        .catch((err) => {
          reject(err);
        });
    });
  },

  delete(url, data) {
    return new Promise((resolve, reject) => {
      server({
        method: 'delete',
        url,
        data,
      })
        .then((res) => {
          resolve(res.data);
        })
        .catch((err) => {
          reject(err);
        });
    });
  },

  validate(url, data, loading, warning, checkExist = false) {
    return new Promise((resolve, reject) => {
      server({
        method: 'get',
        url,
        params: data,
      })
        .then((res) => {
          loading.value = false;
          warning.value = false;
          let target = !res.data.data.length;
          let mesg = '该对象已存在，请重新命名';
          if (checkExist) {
            target = !target;
            mesg = '对象不存在，请检查是否拼写错误';
          }
          if (target) {
            resolve(true);
          } else {
            reject(Error(mesg));
          }
        })
        .catch(() => {
          loading.value = false;
          warning.value = true;
          reject(Error('验证失败，请检查网络连接'));
        });
    });
  },

  downLoad(url, data, tag = null) {
    return new Promise((resolve, reject) => {
      server({
        method: 'get',
        url,
        params: data,
        responseType: 'blob',
      })
        .then((res) => {
          if (res.data.type === 'application/json') {
            window.$message?.error('下载文件内容为空！');
            return;
          }
          if (tag) {
            resolve(res);
          }
          resolve(res.data);
        })
        .catch((err) => {
          reject(err);
        });
    });
  },
};
