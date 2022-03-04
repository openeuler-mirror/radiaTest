import cryptoJs from 'crypto-js';
const key = cryptoJs.enc.Utf8.parse('asdfghjkl123');
const iv = cryptoJs.enc.Utf8.parse('123456789');
function encrypt(word) {
  const srcs = cryptoJs.enc.Utf8.parse(word);
  const encrypted = cryptoJs.AES.encrypt(srcs, key, {
    iv,
    mode: cryptoJs.mode.CBC,
    padding: cryptoJs.pad.ZeroPadding,
  });
  return cryptoJs.enc.Base64.stringify(encrypted.ciphertext);
}
function decrypt(word) {
  const decrypted = cryptoJs.AES.decrypt(word, key, {
    iv,
    mode: cryptoJs.mode.CBC,
    padding: cryptoJs.pad.ZeroPadding,
  });
  return decrypted.toString(cryptoJs.enc.Utf8).toString();
}
export { encrypt, decrypt };
