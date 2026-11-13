package com.sky.Controller.login;

import com.sky.Service.UserService;
import com.sky.constant.JwtClaimsConstant;
import com.sky.dto.UserLoginDto;
import com.sky.entity.User;
import com.sky.properties.JwtProperties;
import com.sky.result.Result;
import com.sky.utils.JwtUtil;
import com.sky.vo.UserLoginVo;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;
@Slf4j
@RestController
@CrossOrigin(origins = "*")
public class LoginController {
    @Autowired
    private JwtProperties jwtProperties;
    @Autowired
    private UserService userService;
    @PostMapping("/login")
    public Result login(@RequestBody UserLoginDto userDto){
        log.info("用户登录：{}",userDto);
        User user = userService.login(userDto);
        //登录成功后，生成jwt令牌
        Map<String, Object> claims = new HashMap<>();
        claims.put(JwtClaimsConstant.USER_ID, user.getId());
        String token = JwtUtil.createJWT(
                jwtProperties.getUserSecretKey(),
                jwtProperties.getUserTtl(),
                claims);

        UserLoginVo userLoginVo = UserLoginVo.builder()
                .id(user.getId())
                .username(user.getUsername())
                .token(token)
                .loginAccount(user.getLoginAccount())
                .isAdmin(user.getIsAdmin())
                .build();

        return Result.success(userLoginVo);
    }
    /**
     * 退出登录
     * @return
     */
    @PostMapping("/logout")
    public Result<String> logout() {
        return Result.success();
    }

}
