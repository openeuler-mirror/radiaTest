class Storage {
  constructor(name) {
    this.name = name;
  }
  getValue (key) {
    if (JSON.parse(localStorage.getItem(this.name))) {
      return JSON.parse(localStorage.getItem(this.name))[key];
    }
    return undefined;
  }
  setValue (key, value) {
    let info = JSON.parse(localStorage.getItem(this.name));
    if (!info) {
      info = {};
    }
    info[key] = value;
    localStorage.setItem(this.name, JSON.stringify(info));
  }
}
export const storage = new Storage('mugenInfo');
