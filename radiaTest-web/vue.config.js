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
  chainWebpack: config => {
    config
      .plugin('html')
      .tap(args => {
        args[0].title = 'radiaTest测试平台';
        return args;
      });
  },
  productionSourceMap: false,
  devServer: {
    host: '172.168.88.197',
    // host: '0.0.0.0',
    port: 8082,
    open: true,
    hot: false,
    compress: true,
    proxy: {
      '/api': {
        target: 'http://123.60.114.22:1457/',
        // target: 'http://0.0.0.0:21500/',
        changeOrigin: true,
        secure: false,
      },
      '/static': {
        target: 'http://123.60.114.22:1457/',
        // target: 'http://0.0.0.0:21500/',
        changeOrigin: true,
        secure: false,
      }
    }
  },
};
