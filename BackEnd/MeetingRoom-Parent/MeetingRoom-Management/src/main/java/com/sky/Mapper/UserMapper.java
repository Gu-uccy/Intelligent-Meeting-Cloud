package com.sky.Mapper;

import com.github.pagehelper.Page;
import com.sky.annotation.AutoFill;
import com.sky.dto.UserPageDto;
import com.sky.entity.User;
import com.sky.enumeration.OperationType;
import com.sky.vo.UserVo;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Update;

import java.util.List;

@Mapper
public interface UserMapper {
    /**
     * 根据用户名查询用户
     * @param loginAccount
     * @return
     */
    @Select("select * from user where login_account = #{loginAccount}")
    User getByUsername(String loginAccount);

    /**
     * 插入用户数据
     * @param user1
     */
    @AutoFill(value = OperationType.INSERT)
    int insertUser(User user1);

    /**
     * 分页查询用户
     * @return
     */
    Page<UserVo> limitSelect(UserPageDto userPageDto);

    /**
     * 批量删除用户
     * @param ids
     * @return
     */
    int deleteByIds(@Param("ids") List<Integer> ids);

    /**
     * 修改用户信息
     * @param user
     * @return
     */
    @AutoFill(value = OperationType.UPDATE)
    int update(User user);

    /**
     * 根据id查询用户
     * @param id
     * @return
     */
    User getById(Integer id);

    /**
     *
     * @param LoginAccount
     * @return
     */
    @Select("select count(1) from user where login_account = #{LoginAccount}")
    int countByUsername(String LoginAccount);

    /**
     * 给新用户分配默认角色（role.is_default = 1，目前是 ROLE_USER）。
     * 注册与管理员新增用户都走这里，保证「注册即入角色」，RBAC 才有起点。
     */
    @org.apache.ibatis.annotations.Insert(
            "INSERT INTO user_role (user_id, role_id, create_by) "
            + "SELECT #{userId}, r.id, 'register' FROM role r WHERE r.is_default = 1 LIMIT 1")
    int assignDefaultRole(@org.apache.ibatis.annotations.Param("userId") Integer userId);
}
