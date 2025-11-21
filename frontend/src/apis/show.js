import request from '@/utils/request'

// 获取计算结果数据，用于展示
export const getCalculateShowAxios = () => request.get('/swmm/show')

export const getPowerStationData = () => request.get('/swmm/show/powerstation/data')
