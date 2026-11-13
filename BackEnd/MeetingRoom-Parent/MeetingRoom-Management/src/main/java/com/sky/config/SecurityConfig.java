package com.sky.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.config.annotation.authentication.configuration.AuthenticationConfiguration;
import org.springframework.security.config.annotation.method.configuration.EnableGlobalMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
@EnableGlobalMethodSecurity(prePostEnabled = true,securedEnabled = true)
public class SecurityConfig {


    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    @Bean
    public AuthenticationManager authenticationManager(AuthenticationConfiguration config) throws Exception {
        return config.getAuthenticationManager();
    }


    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
                .csrf().disable()
                .sessionManagement().sessionCreationPolicy(SessionCreationPolicy.STATELESS)
                .and()
                .authorizeRequests()
                .requestMatchers("/login","/user/login","/api/login","/register").permitAll()
                .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
                .requestMatchers("/**").permitAll()
                // 添加以下Swagger相关路径的放行规则
                .requestMatchers( "/doc.html",                  // knife4j的UI路径
                        "/swagger-ui.html",           // Swagger2默认UI路径
                        "/swagger-ui/**",             // Swagger3的UI资源路径
                        "/webjars/**",                // 第三方UI依赖资源
                        "/swagger-resources/**",      // Swagger的资源配置
                        "/v2/api-docs",               // Swagger2的接口文档
                        "/v2/api-docs-ext",           // 扩展接口文档
                        "/v3/api-docs",               // Swagger3的接口文档
                        "/v3/api-docs/**").permitAll()             // Swagger3的接口文档资源).permitAll()
                .anyRequest().authenticated();

        return http.build();
    }
}
