import axios from 'axios';
// import router from './router/index';
import { storage } from './assets/utils/storageUtils';
import router from './router';

//url接口头定义
const server = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json;charset=UTF-8'
  }
});
// axios.defaults.baseURL = '/api';

//post请求头
// axios.defaults.headers.post['Content-Type'] = 'application/json;charset=UTF-8';
//设置超时
//axios.defaults.timeout = 10000

// axios.defaults.withCredentials = true;

//请求拦截器
server.interceptors.request.use(
  config => {
    let token;
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
  error => {
    return Promise.reject(error);
  }
);
//回应拦截器
server.interceptors.response.use(
  response => {
    if (response.data.error_code === 200 || response.data.error_code === '2000' || !response.data.error_code) {
      response.headers.authorization && storage.setValue('token', response.headers.authorization);
      return Promise.resolve(response);
    }
    return Promise.reject(response);
  },
  error => {
    if (error.response.status === 401) {
      window.$message?.destroyAll();
      window.$message?.error('请重新登陆');
      router.push({
        name: 'login',
      });
    }
    return Promise.reject(error.response || error);
  }
);

//方法定义
export default {
  post(url, data) {
    return new Promise((resolve, reject) => {
      server({
        method: 'post',
        url,
        data,
      })
        .then(res => {
          resolve(res.data);
        })
        .catch(err => {
          reject(err);
        });
    });
  },

  get(url, data) {
    return new Promise((resolve, reject) => {
      server({
        method: 'get',
        url,
        params: data,
      })
        .then(res => {
          resolve(res.data);
        })
        .catch(err => {
          reject(err);
        });
    });
  },

  put(url, data) {
    return new Promise((resolve, reject) => {
      server({
        method: 'put',
        url,
        data,
      })
        .then(res => {
          resolve(res.data);
        })
        .catch(err => {
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
        .then(res => {
          resolve(res.data);
        })
        .catch(err => {
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
          let target = !res.data.length;
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
};
