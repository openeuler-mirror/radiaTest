import { encrypt, decrypt } from './crypto';
class Storage {
  constructor(name) {
    this.name = name;
  }
  getValue (key) {
    try {
      if (JSON.parse(decrypt(sessionStorage.getItem(this.name)))) {
        return JSON.parse(decrypt(sessionStorage.getItem(this.name)))[key];
      }
    } catch (err) {
      window.$message?.error(err.message);
    }
    return undefined;
  }
  setValue (key, value) {
    let info;
    try {
      info = JSON.parse(decrypt(sessionStorage.getItem(this.name)));
    } catch {
      info = JSON.parse(sessionStorage.getItem(this.name));
    }
    if (!info) {
      info = {};
    }
    info[key] = value;
    sessionStorage.setItem(this.name, encrypt(JSON.stringify(info)));
  }
}
export const storage = new Storage('mugenInfo');
