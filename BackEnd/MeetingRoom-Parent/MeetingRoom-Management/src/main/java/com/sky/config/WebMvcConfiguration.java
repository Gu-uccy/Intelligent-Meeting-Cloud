package com.sky.config;

import com.sky.interceptor.JwtTokenUserInterceptor;
import com.sky.json.JacksonObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.converter.HttpMessageConverter;
import org.springframework.http.converter.json.MappingJackson2HttpMessageConverter;
import org.springframework.web.servlet.config.annotation.*;

import org.springframework.web.filter.CorsFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import java.util.List;

/**
 * 配置类，注册web层相关组件
 */
@Configuration
@Slf4j

public class WebMvcConfiguration extends WebMvcConfigurationSupport  {


    @Autowired
    private JwtTokenUserInterceptor jwtTokenUserInterceptor;


    @Bean
    public CorsFilter corsFilter() {
        CorsConfiguration config = new CorsConfiguration();
        config.addAllowedOriginPattern("*");
        config.addAllowedHeader("*");
        config.addAllowedMethod("*");
        config.setAllowCredentials(true);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }
    /**
     * 注册自定义拦截器
     *
     * @param registry
     */
    public void addInterceptors(InterceptorRegistry registry) {
        log.info("开始注册自定义拦截器...");
        registry.addInterceptor(jwtTokenUserInterceptor)
                .addPathPatterns("/**")
                .excludePathPatterns(
                        "/login",
                        "/user/login",
                        "/api/login",
                        "/doc.html",
                        "/webjars/**",
                        "/swagger-resources/**",
                        "/v2/api-docs",
                        "/v2/api-docs-ext",
                        "/swagger-ui.html",
                        "/swagger-resources/configuration/ui",
                        "/swagger-resources/configuration/security");

    }
   /* *//**
     * 通过knife4j生成接口文档
     * @return
     *//*
    @Bean
    public Docket docket1() {
        ApiInfo apiInfo = new ApiInfoBuilder()
                .title("智能会议室接口文档")
                .version("2.0")
                .description("智能会议室接口文档")
                .build();
        Docket docket = new Docket(DocumentationType.SWAGGER_2)
                .groupName("管理端接口")
                .apiInfo(apiInfo)
                .select()
                .apis(RequestHandlerSelectors.basePackage("com.sky.Controller"))
                .paths(PathSelectors.any())
                .build();
        return docket;
    }
*/
    /**
     * 设置静态资源映射
     * @param registry
     */
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler("/doc.html").addResourceLocations("classpath:/META-INF/resources/");
        registry.addResourceHandler("/favicon.ico").addResourceLocations("classpath:/static/");

        registry.addResourceHandler("/webjars/**").addResourceLocations("classpath:/META-INF/resources/webjars/");
    }

    @Override
    public void extendMessageConverters(List<HttpMessageConverter<?>> converters) {
        log.info("扩展消息转换器...");
        //创建消息转换器对象
        MappingJackson2HttpMessageConverter converter=new MappingJackson2HttpMessageConverter();
        //为消息转换器设置对象转换器,对象转换器可以将java对象序列化为json序列
        converter.setObjectMapper(new JacksonObjectMapper());
        //将自己的消息转换器加入容器
        converters.add(0,converter);

    }
}
