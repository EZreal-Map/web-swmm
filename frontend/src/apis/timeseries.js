import resquest from '@/utils/request'

// 获取所有时间序列
// export const getAllTimeSeriesAxios = () => resquest.get('/swmm/timeseries')
// 获取所有时间序列名称
export const getAllTimeSeriesNameAxios = () => resquest.get('/swmm/timeseries/name')
// 通过时间序列ID获取时间序列
export const getTimeseriesByIdAxios = (id) => resquest.get(`/swmm/timeseries/${id}`)
// 通过时间序列ID更新时间序列所有属性
export const updateTimeseriesByIdAxios = (id, data) => {
  data.data = data.data
    .filter(([x, y]) => x && y) // 排除 undefined / '' / null 的数据
    .sort((a, b) => a[0] - b[0]) // 按照 X 坐标升序排序
  return resquest.put(`/swmm/timeseries/${id}`, data)
}
// 增加一个时间序列
export const createTimeseriesAxios = (data) => resquest.post('/swmm/timeseries', data)

// 删除一个时间序列
export const deleteTimeseriesByIdAxios = (id) => resquest.delete(`/swmm/timeseries/${id}`)
