const path = require('path');
const NodePolyfillPlugin = require('node-polyfill-webpack-plugin');
module.exports = {
  pwa: {
    iconPaths: {
      favicon32: 'favicon.ico',
      favicon16: 'favicon.ico',
      appleTouchIcon: 'favicon.ico',
      maskIcon: 'favicon.ico',
      msTileImage: 'favicon.ico'
    }
  },
  chainWebpack: (config) => {
    config.plugin('html').tap((args) => {
      args[0].title = 'radiaTest测试平台';
      return args;
    });
    config.module
      .rule('md')
      .test(/\.md/)
      .use('html-loader')
      .loader('html-loader')
      .end()
      .use('remark-loader')
      .loader('remark-loader')
      .options({
        remarkOptions: {
          plugins: [
            import('remark-html')]
        }
      });
  },
  productionSourceMap: false,
  configureWebpack: {
    plugins: [
      require('unplugin-auto-import/webpack')({
        imports: ['vue', 'vue-router'],
        eslintrc: {
          enabled: true
        }
      }),
      require('unplugin-vue-components/webpack')({dts: true}),
      new NodePolyfillPlugin()
    ],
    resolve: {
      // 配置路径别名
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
  },
  devServer: {
    host: '10.211.55.3',
    port: 8080,
    // https: {
    //   key: '/etc/radiaTest/server_ssl/private/cakey.pem',
    //   cert: '/etc/radiaTest/server_ssl/cacert.pem'
    // },
    open: true,
    hot: false,
    compress: true,
    proxy: {
      '/api': {
        target: 'http://0.0.0.0:21500/',
        changeOrigin: true,
        secure: false
      },
      '/static': {
        target: 'http://0.0.0.0:21500/',
        changeOrigin: true,
        secure: false
      },
      '/socket.io': {
        target: 'http://0.0.0.0:21500/',
        changeOrigin: true,
        // ws: true,
      },
    }
  }
};
