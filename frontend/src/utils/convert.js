// 把字典对象的键从驼峰命名法转换为短横线命名法
// 例如：{ userName: 'John' } => { user_name: 'John' }
// 这个函数会递归处理嵌套对象和数组
// 如果对象的键是字符串，则会转换为小写字母和短横线连接的形式
// 增加了过滤掉空字符串
// 例如：{ userName: '', age: 25 } => { age: 25 }
export const convertKeysToKebabCase = (obj) => {
  if (Array.isArray(obj)) {
    return obj
      .map(convertKeysToKebabCase) // 递归处理数组项
      .filter((item) => item !== '') // 仅过滤掉空字符串
  } else if (obj !== null && typeof obj === 'object') {
    return Object.entries(obj).reduce((acc, [key, value]) => {
      if (value === '') return acc // 过滤空字符串
      const newKey = key.replace(/([a-z])([A-Z])/g, '$1_$2').toLowerCase() // 驼峰转短横线
      acc[newKey] = convertKeysToKebabCase(value) // 递归处理
      return acc
    }, {})
  } else {
    return obj // 其他类型值直接返回
  }
}

// 获取字符串中第一个短横线后面的部分
// 例如：'junction#节点1' => '节点1'
// 例如：'junction#1#1' => '1#1'
// 因为提高 Cesium Entity 的 id 鲁棒性，每次渲染Entity id的时候都加了不同的前缀
// 比如 id : junction#节点名称
// 但是在更新节点的时候需要去掉这个前缀
// 这个函数用于获取第一个短横线后面的部分
export const getStringAfterFirstDash = (str) => {
  const index = str.indexOf('#')
  if (index !== -1) {
    return str.slice(index + 1)
  }
  return str // 如果没有找到短横线，则返回原字符串
}
