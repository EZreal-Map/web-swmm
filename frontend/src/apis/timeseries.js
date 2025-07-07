import resquest from '@/utils/request'
import { formatDateToISO } from '@/utils/convert'

// 获取所有时间序列
// export const getAllTimeSeriesAxios = () => resquest.get('/swmm/timeseries')
// 获取所有时间序列名称
export const getAllTimeSeriesNameAxios = (type) =>
  resquest.get('/swmm/timeseries/name', { params: { type } })
// 通过时间序列ID获取时间序列
export const getTimeseriesByIdAxios = (id, type) =>
  resquest.get(`/swmm/timeseries/${id}`, { params: { type } })
// 通过时间序列ID更新时间序列所有属性
export const updateTimeseriesByIdAxios = (id, data, type) => {
  data.data = data.data
    .filter(([x, y]) => x && y) // 排除 undefined / '' / null 的数据
    .sort((a, b) => a[0] - b[0]) // 按照 X 坐标升序排序
    .map(([x, y]) => [formatDateToISO(x), y])

  return resquest.put(`/swmm/timeseries/${id}`, data, { params: { type } })
}
// 增加一个时间序列
export const createTimeseriesAxios = (data, type) =>
  resquest.post('/swmm/timeseries', data, { params: { type } })

// 删除一个时间序列
export const deleteTimeseriesByIdAxios = (id, type) =>
  resquest.delete(`/swmm/timeseries/${id}`, { params: { type } })
