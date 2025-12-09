import request from '@/utils/request'
import { formatDateToISO } from '@/utils/convert'

// 获取计算选项
export const getCalculateOptionsAxios = () => request.get('/swmm/calculate/options')

// 更新计算选项
export const updateCalculateOptionsAxios = (data) => {
  // 拷贝 data -> payload，防止影响到外面的原数据
  // 将 data.report_step 时间格式转换为 HH:mm:ss，符合后端 time 格式要求
  const payload = {
    ...data,
    report_step: data.report_step.toTimeString().split(' ')[0], // 格式化时间
  }
  // 把payload里面的start_datetime和end_datetime格式化时区
  payload.start_datetime = formatDateToISO(payload.start_datetime)
  payload.end_datetime = formatDateToISO(payload.end_datetime)
  payload.start_report_datetime = formatDateToISO(payload.start_report_datetime)
  return request.put('/swmm/calculate/options', payload)
}

// 通过 name 查询实体属于 node/link 并返回 el-select 选项
export const getQueryEntityKindSelectAxios = (name) => {
  return request.get('/swmm/calculate/result/kind', { params: { name } })
}

// 通过kind ，name，variable 查询实体的计算结果
export const getQueryEntityResultAxios = (kind, name, variable) => {
  return request.get('/swmm/calculate/result', { params: { kind, name, variable } })
}

// 进行计算
export const calculateAxios = () => request.post('/swmm/calculate/run')
