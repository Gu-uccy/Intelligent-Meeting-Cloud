# 九张截图矩阵

全部来自 browser_acceptance.mjs，数据是 API 夹具和业务 mock，水印说明“非现场硬件读数”。分辨率为视口，fullPage PNG 的高度可能更大。

| 文件 | 视口 | 验证内容 |
|---|---|---|
| [01](../screenshots/01_room3d_1920x1080.png) | 1920×1080 | 桌面全景及状态卡片 |
| [02](../screenshots/02_room3d_1366x768.png) | 1366×768 | 笔记本布局、可滚动侧栏 |
| [03](../screenshots/03_room3d_1024x768.png) | 1024×768 | 小屏桌面、卡片分两行 |
| [04](../screenshots/04_room3d_390x844.png) | 390×844 | 手机纵向、导航横滚、数据不盖住模型 |
| [05](../screenshots/05_door_open.png) | 1366×768 | 门指令回写与模型 |
| [06](../screenshots/06_light_off.png) | 1366×768 | 照明关闭 |
| [07](../screenshots/07_smoke_alarm.png) | 1366×768 | 烟雾越界 |
| [08](../screenshots/08_sensor_partial.png) | 1366×768 | 温湿度缺失 --、门灯保留 |
| [09](../screenshots/09_service_disconnected.png) | 1366×768 | 503 断连提示 |

自动断言检查尺寸和状态，人工查看模型可见、文字与水印。9 张表示不同条件，不是 9 次实物实验。
