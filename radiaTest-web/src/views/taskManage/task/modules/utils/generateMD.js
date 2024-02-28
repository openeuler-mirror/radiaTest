import axios from 'axios';
function generateMDByTemplate(isVersionTask) {
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

