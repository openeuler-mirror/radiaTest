import { ref } from 'vue';
import axios from '@/axios.js';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
const caseInfo = ref({});
const detailsList = ref([
  {
    title: '基础信息', name: 'baseInfo', rows: [
      { cols: [{ label: '标题', value: 'xxx'}, { label: '用例', value: 'xxx'}] },
      { cols: [{ label: '测试级别', value: '高' },{label:'测试类型',value:'A'}] },
      { cols: [{ label: '责任人', value: '小明' },{label:'创建时间',value:'2021-1-01-01'}] },
      { cols: [{ label: '修改人', value: '小红' },{label:'更新时间',value:'2021-1-01-02'}] },
      { cols: [{label:'是否自动化',value:'是'}] },
    ]
  },
  {
    title: '用例详情', name: 'caseDetails', rows: [
      { cols: [{ label: '描述', value: 'xxx' }] },
      { cols: [{ label: '预置条件', value: '条件XXXX' }] },
      { cols: [{ label: '测试步骤', value: '步骤12333' }] },
      { cols: [{ label: '预期结果', value: '12333' }] },
      { cols: [{ label: '备注', value: 'qwert' }] },
    ]
  },
  {
    title: '执行信息', name: 'info', rows: [
      { cols: [{ label: '执行框架', value: 'xxx' }, { label: '是否已适配', value: '是' }] },
      { cols: [{ label: '代码仓', value: '123' }, { label: '相对路径', value: '/xxx' }] },
    ]
  }
]);
function setDataList(Info){
  detailsList.value = [
    {
      title: '基础信息', name: 'baseInfo', rows: [
        { cols: [{ label: '标题', value: Info.title}, { label: '用例', value:Info.name}] },
        { cols: [{ label: '测试级别', value: Info.test_level},{label:'测试类型',value:Info.test_type}] },
        { cols: [{ label: '责任人', value:Info.owner },{label:'是否自动化',value:Info.automatic?'是':'否'}] },
        { cols: [{label:'创建时间',value:formatTime(Info.create_time, 'yyyy-MM-dd hh:mm:ss')},{label:'更新时间',value:formatTime(Info.update_time, 'yyyy-MM-dd hh:mm:ss')}] }
      ]
    },
    {
      title: '用例详情', name: 'caseDetails', rows: [
        { cols: [{ label: '描述', value: Info.description,type:'pre'}] },
        { cols: [{ label: '预置条件', value: Info.preset,type:'pre' }] },
        { cols: [{ label: '测试步骤', value: Info.steps,type:'pre' }] },
        { cols: [{ label: '预期结果', value: Info.expection,type:'pre' }] },
        { cols: [{ label: '备注', value: Info.remark,type:'pre' }] },
      ]
    },
    {
      title: '执行信息', name: 'info', rows: [
        { cols: [{ label: '执行框架', value: Info.framework.name}, { label: '是否已适配', value: Info.framework.adaptive?'是':'否'}] },
        { cols: [{ label: '代码仓', value: Info.framework.url }, { label: '相对路径', value: Info.framework.logs_path}] },
      ]
    }
  ];
}
function getDetail (caseId) {
  axios.get(`/v1/baseline/${caseId}`).then(res => {
    axios.get('/v1/case', {
      id: res.data.case_id
    }).then(response => {
      [caseInfo.value] = response;
      caseInfo.value.title = res.data.title;
      axios.get('/v1/framework',{id:response[0].framework_id}).then(result=>{
        [caseInfo.value.framework] = result;
        setDataList(caseInfo.value);
      });
      if(!caseInfo.value.code){
        caseInfo.value.code = '';
      }
    }).catch(err => window.$message?.error(err.data.error_msg || '未知错误'));
  }).catch(err => {
    window.$message?.error(err.data.error_msg ||'未知错误');
  });
}

export {
  caseInfo,
  detailsList,
  getDetail,
};
