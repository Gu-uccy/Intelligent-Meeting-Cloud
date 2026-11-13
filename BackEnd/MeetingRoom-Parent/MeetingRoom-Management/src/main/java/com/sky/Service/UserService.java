package com.sky.Service;

import com.sky.dto.UserLoginDto;
import com.sky.dto.UserPageDto;
import com.sky.entity.User;
import com.sky.result.PageResult;

import java.util.List;

public interface UserService {
    /**
     * 用户登录
     * @param userDto
     * @return
     */
    User login(UserLoginDto userDto);

    /**
     * 添加用户
     * @param user
     * @return
     */
    int addUser(User user);

    /**
     * 分页查询用户
     * @param userPageDto
     * @return
     */
    PageResult pageSelect(UserPageDto userPageDto);

    /**
     * 修改用户信息
     * @param user
     * @return
     */
    int update(User user);

    /**
     * 删除用户
     * @param id
     * @return
     */
    int delete(List<Integer> id);

    /**
     * 设置用户状态
     * @param status
     * @return
     */
    int setActive(Integer status ,Integer  id);

    /**
     * 根据id查询用户信息
     * @param id
     * @return
     */
    User getById(Integer id);


    /**
     * 检查用户名是否存在
     * @param loginAccount
     * @return
     */
    boolean checkUsernameExists(String loginAccount);
}
