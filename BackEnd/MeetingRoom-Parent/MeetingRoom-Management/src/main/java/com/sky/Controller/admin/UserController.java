package com.sky.Controller.admin;

import com.sky.Service.UserService;
import com.sky.constant.JwtClaimsConstant;
import com.sky.dto.UserLoginDto;
import com.sky.dto.UserPageDto;
import com.sky.entity.User;
import com.sky.properties.JwtProperties;
import com.sky.result.PageResult;
import com.sky.result.Result;
import com.sky.utils.JwtUtil;
import com.sky.vo.UserLoginVo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;

import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/admin/user")
@CrossOrigin(origins = "*")
public class UserController {
    @Autowired
    private UserService userService;

    /**
     * 添加用户
     * @param user
     * @return
     */

    @PostMapping
    public Result addUser(@RequestBody User user){
        log.info("添加用户：{}",user);
        return userService.addUser(user)>0?Result.success():Result.error("添加用户失败");
    }

    /**
     * 分页查询用户
     * @param userPageDto
     * @return
     */
    @GetMapping("/page")
    public Result<PageResult> pageSelect( UserPageDto userPageDto){
        log.info("分页查询用户");
        PageResult pageResult = userService.pageSelect(userPageDto);
        return Result.success(pageResult);
    }
    /**
     * 修改用户
     * @param user
     * @return
     */
    @PutMapping
    public Result update(@RequestBody User user){
        log.info("修改用户:{}",user);
        return userService.update(user)>0?Result.success():Result.error("修改用户失败");
    }
    /**
     * 删除用户
     * @param ids
     * @return
     */

    @DeleteMapping
    public Result delete(@RequestParam(value = "ids") List<Integer> ids){
        log.info("批量删除用户:{}",ids);
        return userService.delete(ids)>0?Result.success():Result.error("删除用户失败");
    }
    /**
     * 设置用户激活状态
     * @param status
     * @return
     */
    @PutMapping("/active/{status}")
    public Result setActive(@PathVariable Integer status ,Integer id){
        log.info("设置用户激活状态:{},{}",status, id);
        return userService.setActive(status,id)>0?Result.success():Result.error("设置失败");
    }
    /**
     * 根据id查询用户信息
     * @param id
     * @return
     */

    @GetMapping("/{id}")
    public Result<User> getById(@PathVariable Integer id){
        log.info("查询用户信息:{}",id);
        return Result.success(userService.getById(id));
    }
}
