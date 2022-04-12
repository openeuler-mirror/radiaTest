function textDialog(type, title, content, confirm) {
  const d =
    window.$dialog &&
    window.$dialog[type]({
      title,
      content,
      positiveText: '确定',
      negativeText: '取消',
      onPositiveClick: () => {
        confirm && confirm();
        d.destroy();
      },
      onNegativeClick: () => {
        d.destroy();
      },
    });
}
export default textDialog;
