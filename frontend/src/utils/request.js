import axios from 'axios'

// const baseURL = 'http://127.0.0.1:8080' // 本地开发
// const baseURL = 'http://172.25.146.121:8080' // 远程临时展示
const baseURL = '/api' // 反向代理（部署时使用）

const instance = axios.create({
  baseURL,
  timeout: 100000,
})

// 请求拦截器
instance.interceptors.request.use(
  (config) => {
    return config
  },
  (err) => Promise.reject(err),
)

// 响应拦截器
instance.interceptors.response.use(
  (res) => {
    if (res.status === 200) {
      return res.data // 返回核心响应数据，可能需要根据实际情况进行调整
    }
    // return Promise.reject(res.data)
  },
  (err) => {
    ElMessage.error(err.response.data.detail)
    return Promise.reject(err)
  },
)

export default instance
export { baseURL }
