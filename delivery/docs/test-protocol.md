# 可复现测试协议

## 隔离接口

运行 `python delivery/tests/test_sensor_contract.py`，强制 simulation，使用临时数据目录及 Flask test_client。GPIO/PWM 故障用替身覆盖，32 条用例不会向实物发指令。断言与结果见用例清单、backend_tests.json。

## 浏览器

Browser plugin 不可用，按前端测试技能回退 Playwright，使用已安装 Chrome，版本写入 browser_tests.json。默认地址 5188，可用 ACCEPTANCE_URL 覆盖。模块从 node_modules 或 PLAYWRIGHT_MODULE_PATH 解析。

使用独立模拟环境：

```powershell
# 终端 A，仓库根目录
$env:MEETING_DATA_MODE='simulation'; $env:MEETING_PORT='5058'
python Flask/unified_meeting_room_system.py
# 终端 B，仓库根目录
$env:VITE_USE_MOCK='true'; $env:VITE_SENSOR_PROXY_TARGET='http://127.0.0.1:5058'
$env:VITE_PORT='5188'
npm --prefix FrontEnd/Intelligent_meeting_cloud run dev -- --host 127.0.0.1 --port 5188 --strictPort
# 终端 C，等待至少一个采样周期
node delivery/tests/browser_acceptance.mjs
```

20 条用例用独立浏览器上下文，预约用内置 mock，current/control 拦截为夹具；导出继续请求真实本地模拟 Flask。故障注入只影响测试浏览器，不停止现场服务。截图带水印，不得移除后冒充实测。预约选择明日空闲时段。

四档检查页面横向溢出、数值卡片文本宽度、手机端模型与面板不重叠。截图另经人工查看；浏览器 pageerror 为空才通过。性能采样没有未经协商的业务 SLA。

## 构建与汇总

运行 npm run build:frontend，保存实际退出码和日志。运行 python delivery/build_evidence.py，汇总 52 用例 CSV/JSON、报告、文档目录、SHA256。输入结果不得手工改成 PASS。复测时要同时更新预检，实物和真实业务另填现场表。
