import { ElMessage } from 'element-plus'

const showMessage = (message, type = 'success') => {
  ElMessage({
    message,
    type,
    duration: 2000,
    grouping: true, 
  })
}

export const toast = {
  success: (msg) => showMessage(msg, 'success'),
  warning: (msg) => showMessage(msg, 'warning'),
  error: (msg) => showMessage(msg, 'error'),
  info: (msg) => showMessage(msg, 'info'),
}