import { encrypt, decrypt } from './crypto';
class Storage {
  constructor(name) {
    this.name = name;
  }
  getValue(key) {
    if (JSON.parse(decrypt(localStorage.getItem(this.name)))) {
      return JSON.parse(decrypt(localStorage.getItem(this.name)))[key];
    }
    return undefined;
  }
  setValue(key, value) {
    let info;
    try {
      info = JSON.parse(decrypt(localStorage.getItem(this.name)));
    } catch {
      info = JSON.parse(localStorage.getItem(this.name));
    }
    if (!info) {
      info = {};
    }
    info[key] = value;
    localStorage.setItem(this.name, encrypt(JSON.stringify(info)));
  }
}
export const storage = new Storage('mugenInfo');
