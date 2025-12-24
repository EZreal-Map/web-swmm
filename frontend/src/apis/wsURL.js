import { baseURL } from '@/utils/request.js'

// WebSocket 地址拼接函数
export const getWebSocketURL = (path) => {
  let wsURL

  // 如果 baseURL 是 http:// 或 https:// 开头，使用完整的 WebSocket 地址
  // 例：baseURL = "https://www.tangkaiwen.cloud/api"，path = "/agent/ws"
  //   wsProtocol = 'wss://'
  //   wsDomain = 'www.tangkaiwen.cloud/api'
  //   wsURL = 'wss://www.tangkaiwen.cloud/api/agent/ws'
  if (baseURL.startsWith('http://') || baseURL.startsWith('https://')) {
    const wsProtocol = baseURL.startsWith('https://') ? 'wss://' : 'ws://'
    const wsDomain = baseURL.replace(/^http(s)?:\/\//, '') // 去掉 http:// 或 https://

    // 拼接 WebSocket URL
    wsURL = `${wsProtocol}${wsDomain}${path}`
  } else {
    // 如果 baseURL 是相对路径，拼接成完整的 WebSocket URL
    // 例1：当前页面 https://www.tangkaiwen.cloud/xxx，baseURL = "/api"，path = "/agent/ws"
    //   wsProtocol = 'wss://'
    //   window.location.host = 'www.tangkaiwen.cloud'
    //   wsURL = 'wss://www.tangkaiwen.cloud/api/agent/ws'
    // 例2：当前页面 http://www.tangkaiwen.cloud:8080/xxx，baseURL = "/api"，path = "/agent/ws"
    //   wsProtocol = 'ws://'
    //   window.location.host = 'www.tangkaiwen.cloud:8080'
    //   wsURL = 'ws://www.tangkaiwen.cloud:8080/api/agent/ws'
    const wsProtocol = window.location.protocol.startsWith('https') ? 'wss://' : 'ws://'
    wsURL = `${wsProtocol}${window.location.host}${baseURL}${path}`
  }

  return wsURL
}

/**
 * 获取 agent chat websocket url
 * @param {string} clientId
 * @returns {string}
 */
export function getChatWSURL(clientId) {
  const baseChatWSURL = getWebSocketURL('/agent/ws')
  return `${baseChatWSURL}/${clientId}`
}
