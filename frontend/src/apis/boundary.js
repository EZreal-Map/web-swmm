import request from '@/utils/request'

// 获取流域边界数据
export const getBoundaryAxios = () => {
  return request.get('/mj/basin_boundary')
}
