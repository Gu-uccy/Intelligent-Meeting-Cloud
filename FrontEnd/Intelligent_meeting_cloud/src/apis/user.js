import request from "@/utils/http";

export const loginAPI = (userDto) => {
  return request({
    url:'/login',
    method:'POST',
    data:userDto
  })
}

export const logoutAPI = () => {
  return request({
    url:'/logout',
    method:'POST'
  })
}

export const registerAPI = (registerForm) => {
  return request({
    url: '/register',
    method: 'POST',
    data: registerForm
  })
}