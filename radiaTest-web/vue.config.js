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
    host: '172.168.131.14',
    port: 1400,
    open: true,
    https: false,
    hot: false,
    compress: true,
    proxy: {
      '/api': {
        target: 'http://172.168.131.14:1401/',
        changeOrigin: true,
        secure: false,
      }
    }
  },
};
