package com.sky.Controller.login;

import com.sky.Service.UserService;
import com.sky.entity.User;
import com.sky.result.Result;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@Slf4j
@RestController
@CrossOrigin(origins = "*")
public class RegisterController {
    @Autowired
    private UserService userService;

    @PostMapping("/register")
    public Result register(@RequestBody User user){
        log.info("用户注册：{}",user);
        // 校验用户名长度
        if (user.getLoginAccount().length() < 2 || user.getLoginAccount().length() > 20) {
            return Result.error("用户名长度必须在2-20位之间");
        }

        // 校验密码长度
        if (user.getPassword().length() < 5 || user.getPassword().length() > 20) {
            return Result.error("密码长度必须在5-20位之间");
        }

        // 检查用户名是否已存在
        if (userService.checkUsernameExists(user.getLoginAccount())) {
            return Result.error("用户名已存在");
        }

       return userService.addUser(user)>0?Result.success():Result.error("注册失败");


    }

}
