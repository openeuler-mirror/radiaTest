export function createAvatar (text, size = 40, textColor = 'rgba(0, 47, 167, 1)', backgoundColor = '#fff') {
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  ctx.font = `${size / 2}px Arial`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = backgoundColor;
  ctx.fillRect(0, 0, size, size);
  ctx.fillStyle = textColor;
  ctx.fillText(text, size / 2, size / 2);
  return canvas.toDataURL('image/jpeg');
}
