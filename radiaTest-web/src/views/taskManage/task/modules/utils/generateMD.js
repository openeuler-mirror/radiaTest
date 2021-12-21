import axios from 'axios';

// const templateOptions = {
//   record: '| date | edition   | describe | author |',
// };
// function renderTable (template, data) {
//   let result = '';
//   for (let item of data) {
//     const keys = Object.keys(item);
//     let element = template;
//     for (let key of keys) {
//       element = element.replace(key, String(item[key]).padEnd(10));
//     }
//     result += `${element}\n`;
//   }
//   return result;
// }
function generateMDByTemplate (isVersionTask) {
  return new Promise((resolve, reject) => {
    const templateUrl = isVersionTask ? '/version.md' : '/template.md';
    axios.get(templateUrl).then(res => {
      resolve(res.data);
    }).catch(err => {
      reject(err);
    });
  });
}
export {
  generateMDByTemplate,
};

