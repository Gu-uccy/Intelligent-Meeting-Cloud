# 52 条可执行测试用例

自动从本轮结果和测试源码汇总。TC_01–32 使用 Flask test_client/GPIO 替身；TC_33–52 使用 Chrome、业务 mock、API 夹具，TC_52 实际下载本地模拟 CSV。没有实物通过项。

| 编号 | 用例 | 结果 | 源码入口 |
|---|---|---|---|
| TC_01 | health | PASS | [test_sensor_contract.py:43](../../delivery/tests/test_sensor_contract.py#L43) |
| TC_02 | partial_keeps_devices | PASS | [test_sensor_contract.py:47](../../delivery/tests/test_sensor_contract.py#L47) |
| TC_03 | missing_dht_never_fabricates | PASS | [test_sensor_contract.py:54](../../delivery/tests/test_sensor_contract.py#L54) |
| TC_04 | hardware_not_simulated | PASS | [test_sensor_contract.py:58](../../delivery/tests/test_sensor_contract.py#L58) |
| TC_05 | simulation_adjusts | PASS | [test_sensor_contract.py:65](../../delivery/tests/test_sensor_contract.py#L65) |
| TC_06 | history_missing_is_null | PASS | [test_sensor_contract.py:71](../../delivery/tests/test_sensor_contract.py#L71) |
| TC_07 | history_provenance | PASS | [test_sensor_contract.py:75](../../delivery/tests/test_sensor_contract.py#L75) |
| TC_08 | empty_export | PASS | [test_sensor_contract.py:81](../../delivery/tests/test_sensor_contract.py#L81) |
| TC_09 | export_roundtrip | PASS | [test_sensor_contract.py:84](../../delivery/tests/test_sensor_contract.py#L84) |
| TC_10 | nonobject_request | PASS | [test_sensor_contract.py:93](../../delivery/tests/test_sensor_contract.py#L93) |
| TC_11 | malformed_json | PASS | [test_sensor_contract.py:96](../../delivery/tests/test_sensor_contract.py#L96) |
| TC_12 | unknown_action | PASS | [test_sensor_contract.py:99](../../delivery/tests/test_sensor_contract.py#L99) |
| TC_13 | unknown_device | PASS | [test_sensor_contract.py:102](../../delivery/tests/test_sensor_contract.py#L102) |
| TC_14 | string_state_rejected | PASS | [test_sensor_contract.py:105](../../delivery/tests/test_sensor_contract.py#L105) |
| TC_15 | negative_brightness | PASS | [test_sensor_contract.py:108](../../delivery/tests/test_sensor_contract.py#L108) |
| TC_16 | excess_brightness | PASS | [test_sensor_contract.py:111](../../delivery/tests/test_sensor_contract.py#L111) |
| TC_17 | dim_light | PASS | [test_sensor_contract.py:114](../../delivery/tests/test_sensor_contract.py#L114) |
| TC_18 | light_on | PASS | [test_sensor_contract.py:118](../../delivery/tests/test_sensor_contract.py#L118) |
| TC_19 | light_off | PASS | [test_sensor_contract.py:122](../../delivery/tests/test_sensor_contract.py#L122) |
| TC_20 | door_open | PASS | [test_sensor_contract.py:126](../../delivery/tests/test_sensor_contract.py#L126) |
| TC_21 | door_close | PASS | [test_sensor_contract.py:131](../../delivery/tests/test_sensor_contract.py#L131) |
| TC_22 | unavailable_servo | PASS | [test_sensor_contract.py:135](../../delivery/tests/test_sensor_contract.py#L135) |
| TC_23 | failed_pwm_no_success_state | PASS | [test_sensor_contract.py:141](../../delivery/tests/test_sensor_contract.py#L141) |
| TC_24 | auto_toggle | PASS | [test_sensor_contract.py:149](../../delivery/tests/test_sensor_contract.py#L149) |
| TC_25 | auto_bool_validation | PASS | [test_sensor_contract.py:152](../../delivery/tests/test_sensor_contract.py#L152) |
| TC_26 | threshold_update | PASS | [test_sensor_contract.py:155](../../delivery/tests/test_sensor_contract.py#L155) |
| TC_27 | threshold_order | PASS | [test_sensor_contract.py:159](../../delivery/tests/test_sensor_contract.py#L159) |
| TC_28 | threshold_type | PASS | [test_sensor_contract.py:162](../../delivery/tests/test_sensor_contract.py#L162) |
| TC_29 | humidity_range | PASS | [test_sensor_contract.py:165](../../delivery/tests/test_sensor_contract.py#L165) |
| TC_30 | stale_sample | PASS | [test_sensor_contract.py:168](../../delivery/tests/test_sensor_contract.py#L168) |
| TC_31 | alarm_priority | PASS | [test_sensor_contract.py:174](../../delivery/tests/test_sensor_contract.py#L174) |
| TC_32 | dual_servo_output | PASS | [test_sensor_contract.py:181](../../delivery/tests/test_sensor_contract.py#L181) |
| TC_33 | 登录页内容与输入框 | PASS | [browser_acceptance.mjs:69](../../delivery/tests/browser_acceptance.mjs#L69) |
| TC_34 | 演示账号登录跳转 | PASS | [browser_acceptance.mjs:70](../../delivery/tests/browser_acceptance.mjs#L70) |
| TC_35 | 会议室列表加载 | PASS | [browser_acceptance.mjs:76](../../delivery/tests/browser_acceptance.mjs#L76) |
| TC_36 | 选择会议室与空闲时间片 | PASS | [browser_acceptance.mjs:77](../../delivery/tests/browser_acceptance.mjs#L77) |
| TC_37 | 提交预约并持久化到演示存储 | PASS | [browser_acceptance.mjs:87](../../delivery/tests/browser_acceptance.mjs#L87) |
| TC_38 | 3D页面身份、主体与无错误覆盖层 | PASS | [browser_acceptance.mjs:93](../../delivery/tests/browser_acceptance.mjs#L93) |
| TC_39 | WebGL画布创建且尺寸有效 | PASS | [browser_acceptance.mjs:97](../../delivery/tests/browser_acceptance.mjs#L97) |
| TC_40 | 模拟接口明确标注 | PASS | [browser_acceptance.mjs:101](../../delivery/tests/browser_acceptance.mjs#L101) |
| TC_41 | 传感器来源映射为实时状态（夹具） | PASS | [browser_acceptance.mjs:102](../../delivery/tests/browser_acceptance.mjs#L102) |
| TC_42 | 温湿度轮询动态更新 | PASS | [browser_acceptance.mjs:103](../../delivery/tests/browser_acceptance.mjs#L103) |
| TC_43 | 人员状态刷新 | PASS | [browser_acceptance.mjs:108](../../delivery/tests/browser_acceptance.mjs#L108) |
| TC_44 | 点击门回写并更新场景状态 | PASS | [browser_acceptance.mjs:109](../../delivery/tests/browser_acceptance.mjs#L109) |
| TC_45 | 点击灯回写并更新场景状态 | PASS | [browser_acceptance.mjs:113](../../delivery/tests/browser_acceptance.mjs#L113) |
| TC_46 | 会议室、氛围与视角切换 | PASS | [browser_acceptance.mjs:118](../../delivery/tests/browser_acceptance.mjs#L118) |
| TC_47 | 烟雾越界显示报警 | PASS | [browser_acceptance.mjs:125](../../delivery/tests/browser_acceptance.mjs#L125) |
| TC_48 | 传感器缺失仍保留门灯且不伪造零值 | PASS | [browser_acceptance.mjs:126](../../delivery/tests/browser_acceptance.mjs#L126) |
| TC_49 | 控制失败保留状态、服务中断与恢复 | PASS | [browser_acceptance.mjs:133](../../delivery/tests/browser_acceptance.mjs#L133) |
| TC_50 | 四档分辨率无水平溢出与截图矩阵 | PASS | [browser_acceptance.mjs:147](../../delivery/tests/browser_acceptance.mjs#L147) |
| TC_51 | 浏览器运行异常与帧间隔采样 | PASS | [browser_acceptance.mjs:164](../../delivery/tests/browser_acceptance.mjs#L164) |
| TC_52 | CSV导出下载闭环 | PASS | [browser_acceptance.mjs:170](../../delivery/tests/browser_acceptance.mjs#L170) |

## 操作与断言

### TC_01 health

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_01_health(self):
    r = self.client.get('/api/health')
    self.assertEqual((r.status_code, r.json['service'], r.json['source']), (200, 'meeting-room-sensors', 'simulation'))
```

### TC_02 partial_keeps_devices

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_02_partial_keeps_devices(self):
    r = self.client.get('/api/current')
    self.assertEqual(r.status_code, 200)
    self.assertEqual(r.json['quality'], 'partial')
    self.assertIsNone(r.json['temperature'])
    self.assertIn('door_open', r.json['devices'])
```

### TC_03 missing_dht_never_fabricates

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_03_missing_dht_never_fabricates(self):
    m.ON_RASPBERRY_PI = True
    self.assertEqual(m.read_dht_sensor(), (None, None))
```

### TC_04 hardware_not_simulated

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_04_hardware_not_simulated(self):
    m.ON_RASPBERRY_PI = True
    (m.current_temp, m.current_humidity) = (45.5, 8.0)
    m.devices['cooling'] = True
    m.simulate_environment_by_devices()
    self.assertEqual((m.current_temp, m.current_humidity), (45.5, 8.0))
```

### TC_05 simulation_adjusts

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_05_simulation_adjusts(self):
    (m.current_temp, m.current_humidity) = (25, 50)
    m.devices['cooling'] = True
    m.simulate_environment_by_devices()
    self.assertEqual(m.current_temp, 24.8)
```

### TC_06 history_missing_is_null

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_06_history_missing_is_null(self):
    m.append_history(None, None, None, False, 20, 20)
    self.assertIsNone(self.client.get('/api/history').json[0]['temperature'])
```

### TC_07 history_provenance

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_07_history_provenance(self):
    m.devices['door_open'] = True
    m.append_history(25, 50, 30, True, 20, 20)
    row = self.client.get('/api/history').json[0]
    self.assertEqual((row['source'], row['door_open']), ('simulation', True))
```

### TC_08 empty_export

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_08_empty_export(self):
    self.assertEqual(self.client.get('/api/export/csv').status_code, 503)
```

### TC_09 export_roundtrip

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_09_export_roundtrip(self):
    m.append_history(25, 50, 30, True, 20, 20)
    r = self.client.get('/api/export/csv')
    rows = list(csv.reader(io.StringIO(r.get_data(as_text=True))))
    self.assertEqual(r.status_code, 200)
    self.assertEqual(rows[0][-2:], ['门指令状态', '数据来源'])
    self.assertEqual(rows[1][-1], 'simulation')
    (RESULTS / 'sample_export.csv').write_bytes(r.data)
```

### TC_10 nonobject_request

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_10_nonobject_request(self):
    self.assertEqual(self.client.post('/api/control', json=[]).status_code, 400)
```

### TC_11 malformed_json

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_11_malformed_json(self):
    self.assertEqual(self.client.post('/api/control', data='{', content_type='application/json').status_code, 400)
```

### TC_12 unknown_action

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_12_unknown_action(self):
    self.assertEqual(self.post(action='reset-everything').status_code, 400)
```

### TC_13 unknown_device

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_13_unknown_device(self):
    self.assertEqual(self.post(action='manual', device='arbitrary', state=True).status_code, 400)
```

### TC_14 string_state_rejected

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_14_string_state_rejected(self):
    self.assertEqual(self.post(action='manual', device='door', state='false').status_code, 400)
```

### TC_15 negative_brightness

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_15_negative_brightness(self):
    self.assertEqual(self.post(action='manual', device='lighting', state=True, brightness=-1).status_code, 400)
```

### TC_16 excess_brightness

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_16_excess_brightness(self):
    self.assertEqual(self.post(action='manual', device='lighting', state=True, brightness=101).status_code, 400)
```

### TC_17 dim_light

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_17_dim_light(self):
    r = self.post(action='manual', device='lighting', state=True, brightness=40)
    self.assertEqual(r.json['devices']['lighting_brightness'], 40)
```

### TC_18 light_on

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_18_light_on(self):
    r = self.post(action='manual', device='lighting', state=True)
    self.assertTrue(r.json['devices']['lighting'])
```

### TC_19 light_off

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_19_light_off(self):
    r = self.post(action='manual', device='lighting', state=False)
    self.assertEqual(r.json['devices']['lighting_brightness'], 0)
```

### TC_20 door_open

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_20_door_open(self):
    r = self.post(action='manual', device='door', state=True)
    self.assertTrue(r.json['devices']['door_open'])
    self.assertEqual(r.json['door_state_kind'], 'commanded')
```

### TC_21 door_close

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_21_door_close(self):
    m.devices['door_open'] = True
    self.assertFalse(self.post(action='manual', device='door', state=False).json['devices']['door_open'])
```

### TC_22 unavailable_servo

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_22_unavailable_servo(self):
    m.ON_RASPBERRY_PI = True
    r = self.post(action='manual', device='door', state=True)
    self.assertEqual(r.status_code, 503)
    self.assertFalse(m.devices['door_open'])
```

### TC_23 failed_pwm_no_success_state

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_23_failed_pwm_no_success_state(self):
    m.ON_RASPBERRY_PI = True
    bad = Mock()
    bad.ChangeDutyCycle.side_effect = RuntimeError('test driver failure')
    m.door_servos = {'left': bad, 'right': Mock()}
    self.assertEqual(self.post(action='manual', device='door', state=True).status_code, 503)
    self.assertFalse(m.devices['door_open'])
```

### TC_24 auto_toggle

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_24_auto_toggle(self):
    self.assertFalse(self.post(action='set_auto', enabled=False).json['devices']['auto_mode'])
```

### TC_25 auto_bool_validation

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_25_auto_bool_validation(self):
    self.assertEqual(self.post(action='set_auto', enabled='true').status_code, 400)
```

### TC_26 threshold_update

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_26_threshold_update(self):
    self.assertEqual(self.post(action='set_params', temp_min=18, temp_max=28).status_code, 200)
    self.assertEqual(m.TEMP_MIN, 18)
```

### TC_27 threshold_order

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_27_threshold_order(self):
    self.assertEqual(self.post(action='set_params', temp_min=30, temp_max=20).status_code, 400)
```

### TC_28 threshold_type

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_28_threshold_type(self):
    self.assertEqual(self.post(action='set_params', temp_min='hot').status_code, 400)
```

### TC_29 humidity_range

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_29_humidity_range(self):
    self.assertEqual(self.post(action='set_params', humidity_max=120).status_code, 400)
```

### TC_30 stale_sample

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_30_stale_sample(self):
    m.ON_RASPBERRY_PI = True
    (m.current_temp, m.current_humidity, m.last_dht_success) = (25, 50, time.time() - 30)
    r = self.client.get('/api/current')
    self.assertEqual((r.json['quality'], r.json['sensor_status']['climate']), ('partial', 'stale'))
```

### TC_31 alarm_priority

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_31_alarm_priority(self):
    m.devices['alarm'] = True
    with patch.object(m, 'set_rgb_color') as red, patch.object(m, 'set_rgb_brightness') as white:
        m.apply_device_outputs()
        red.assert_called_once_with('red')
        white.assert_not_called()
```

### TC_32 dual_servo_output

范围：isolated Flask test client / GPIO doubles。结果：PASS。

```python
def test_32_dual_servo_output(self):
    m.ON_RASPBERRY_PI = True
    m.door_servos = {'left': Mock(), 'right': Mock()}
    m.set_door_servo(True)
    for servo in m.door_servos.values():
        servo.ChangeDutyCycle.assert_called_once_with(m.SERVO_OPEN_DUTY)
```

### TC_33 登录页内容与输入框

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(33, '登录页内容与输入框', async () => { await page.goto(`${base}/login`); await waitVisible(page.locator('.sign-in-form').getByPlaceholder('用户名', { exact: true })); assert.match(await page.title(), /智会云/); });
```

### TC_34 演示账号登录跳转

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(34, '演示账号登录跳转', async () => {
    await page.locator('.sign-in-form').getByPlaceholder('用户名', { exact: true }).fill('test_user');
    await page.locator('.sign-in-form input[type=password]').fill('123456');
    await page.locator('.sign-in-form').evaluate(form => form.requestSubmit());
    await page.waitForURL(`${base}/`); assert.ok(await page.evaluate(() => !!localStorage.getItem('user')));
  });
```

### TC_35 会议室列表加载

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(35, '会议室列表加载', async () => { await page.goto(`${base}/booking`); await waitVisible(page.locator('.room-card').first()); });
```

### TC_36 选择会议室与空闲时间片

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(36, '选择会议室与空闲时间片', async () => {
    await page.getByRole('button', { name: '立即预约', exact: true }).first().click();
    const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate()+1);
    const date = `${tomorrow.getFullYear()}-${String(tomorrow.getMonth()+1).padStart(2,'0')}-${String(tomorrow.getDate()).padStart(2,'0')}`;
    await page.locator('.date-picker').fill(date);
    await page.locator('.date-picker').dispatchEvent('change');
    await waitVisible(page.locator('.time-slot.status-0').first());
    await page.locator('.time-slot.status-0').first().click();
    await waitVisible(page.getByPlaceholder('请输入会议主题'));
  });
```

### TC_37 提交预约并持久化到演示存储

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(37, '提交预约并持久化到演示存储', async () => {
    await page.getByPlaceholder('请输入会议主题').fill('交付验收自动测试');
    await page.getByRole('button', { name: '提交预约申请', exact: true }).click();
    await page.waitForFunction(() => Object.values(localStorage).some(v => v.includes('交付验收自动测试')));
    await page.locator('.modal-overlay').waitFor({ state: 'hidden' });
  });
```

### TC_38 3D页面身份、主体与无错误覆盖层

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(38, '3D页面身份、主体与无错误覆盖层', async () => {
    await page.goto(`${base}/room-3d`); await waitVisible(page.getByRole('heading', { name: '3D智能会议室模型展厅' }));
    assert.equal(await page.locator('vite-error-overlay').count(), 0); assert.equal(new URL(page.url()).pathname, '/room-3d');
  });
```

### TC_39 WebGL画布创建且尺寸有效

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(39, 'WebGL画布创建且尺寸有效', async () => {
    await waitVisible(page.locator('.viewport canvas')); const box = await page.locator('.viewport canvas').boundingBox(); assert.ok(box.width > 200 && box.height > 200);
    await page.waitForTimeout(500);
  });
```

### TC_40 模拟接口明确标注

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(40, '模拟接口明确标注', async () => { await waitVisible(page.locator('.status-pill.simulation')); });
```

### TC_41 传感器来源映射为实时状态（夹具）

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(41, '传感器来源映射为实时状态（夹具）', async () => { fixture.source = 'sensor'; await refresh(); await waitVisible(page.locator('.status-pill.live')); });
```

### TC_42 温湿度轮询动态更新

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(42, '温湿度轮询动态更新', async () => {
    fixture.temperature = 28.7; fixture.humidity = 55;
    await page.locator('.sensor-card').filter({ hasText: '温度' }).getByText('28.7℃').waitFor({ timeout: 10000 });
    await waitVisible(page.locator('.sensor-card').filter({ hasText: '湿度' }).getByText('55%'));
  });
```

### TC_43 人员状态刷新

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(43, '人员状态刷新', async () => { fixture.motion = fixture.presence = true; fixture.people_count = 3; await refresh(); await waitVisible(page.locator('.stage-state').getByText('3人', { exact: true })); });
```

### TC_44 点击门回写并更新场景状态

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(44, '点击门回写并更新场景状态', async () => {
    await page.locator('.state-button').click(); await waitVisible(page.locator('.stage-state').getByText('门开', { exact: true })); assert.equal(fixture.door_open, true);
    await screenshot('05_door_open.png', 'door command written back, door open');
  });
```

### TC_45 点击灯回写并更新场景状态

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(45, '点击灯回写并更新场景状态', async () => {
    await page.getByRole('button', { name: /关闭LED灯/ }).click();
    await waitVisible(page.locator('.stage-state').getByText('灯关', { exact: true })); assert.equal(fixture.devices.lighting, false);
    await screenshot('06_light_off.png', 'lighting command written back, light off');
  });
```

### TC_46 会议室、氛围与视角切换

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(46, '会议室、氛围与视角切换', async () => {
    await page.locator('button[title="培训研讨室"]').click();
    await page.getByRole('button', { name: '演示汇报', exact: true }).click();
    await page.getByRole('button', { name: '俯视', exact: true }).click();
    await waitVisible(page.locator('.stage-bar').getByText('培训研讨室', { exact: true }));
    assert.match(await page.locator('.stage-bar').innerText(), /演示汇报/);
  });
```

### TC_47 烟雾越界显示报警

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(47, '烟雾越界显示报警', async () => { fixture.smoke = 180; await refresh(); await waitVisible(page.getByRole('alert').filter({ hasText: '烟雾越界' })); await screenshot('07_smoke_alarm.png', 'smoke threshold alarm fixture'); fixture.smoke = 20; });
```

### TC_48 传感器缺失仍保留门灯且不伪造零值

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(48, '传感器缺失仍保留门灯且不伪造零值', async () => {
    fixture.temperature = fixture.humidity = null; fixture.quality = 'partial'; fixture.sensor_status.climate = 'unavailable';
    await refresh(); await waitVisible(page.locator('.status-pill.partial'));
    assert.equal(await page.locator('.sensor-card').filter({ hasText: '温度' }).locator('strong').innerText(), '--');
    await waitVisible(page.locator('.state-button')); await screenshot('08_sensor_partial.png', 'DHT missing, door and light retained');
    fixture.temperature = 24.5; fixture.humidity = 48; fixture.quality = 'normal'; fixture.sensor_status.climate = 'ok';
  });
```

### TC_49 控制失败保留状态、服务中断与恢复

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(49, '控制失败保留状态、服务中断与恢复', async () => {
    controlFailure = true;
    await page.locator('.state-button').click();
    await waitVisible(page.getByRole('alert').filter({ hasText: '门控制失败' }));
    await waitVisible(page.locator('.stage-state').getByText('门开', { exact: true }));
    await page.getByRole('button', { name: /打开LED灯/ }).click();
    await waitVisible(page.getByRole('alert').filter({ hasText: '灯光控制失败' }));
    await waitVisible(page.locator('.stage-state').getByText('灯关', { exact: true }));
    assert.equal(fixture.door_open, true); assert.equal(fixture.devices.lighting, false);
    controlFailure = false;
    unavailable = true; await refresh(); await waitVisible(page.locator('.status-pill.disconnected'));
    await screenshot('09_service_disconnected.png', 'injected service 503, retained last state');
    unavailable = false; await refresh(); await waitVisible(page.locator('.status-pill.live'));
  });
```

### TC_50 四档分辨率无水平溢出与截图矩阵

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(50, '四档分辨率无水平溢出与截图矩阵', async () => {
    let i = 0;
    for (const [width, height] of [[1920,1080], [1366,768], [1024,768], [390,844]]) {
      await page.setViewportSize({ width, height }); const started = performance.now(); await refresh();
      await page.locator('.viewport canvas').scrollIntoViewIfNeeded(); await page.waitForTimeout(300);
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `overflow at ${width}`);
      assert.ok(await page.locator('.sensor-card strong').evaluateAll(nodes => nodes.every(n => n.scrollWidth <= n.clientWidth + 1)), `sensor text clipped at ${width}`);
      assert.ok(await page.locator('.brand-text').evaluate(n => n.getBoundingClientRect().height < 50), `brand wraps at ${width}`);
      if (width < 641) {
        const canvas = await page.locator('.viewport').boundingBox();
        const dock = await page.locator('.sensor-dock').boundingBox();
        assert.ok(dock.y >= canvas.y + canvas.height, 'mobile cards must not cover the room');
      }
      timings.push({ viewport: `${width}x${height}`, ready_ms: +(performance.now()-started).toFixed(2), scope: 'dev_server_reload_and_state_ready' });
      await screenshot(`0${++i}_room3d_${width}x${height}.png`, 'responsive normal state');
    }
  });
```

### TC_51 浏览器运行异常与帧间隔采样

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(51, '浏览器运行异常与帧间隔采样', async () => {
    assert.deepEqual(errors, []);
    const frames = await page.evaluate(() => new Promise(resolve => { const intervals = []; let prev; const begin = performance.now(); function frame(t) { if (prev) intervals.push(t-prev); prev=t; if(t-begin<2000) requestAnimationFrame(frame); else resolve(intervals); } requestAnimationFrame(frame); }));
    writeFileSync(path.join(out, 'frame_intervals.csv'), 'sample,interval_ms,scope\n' + frames.map((v,i)=>`${i+1},${v.toFixed(3)},headless_browser_raf`).join('\n'));
    assert.ok(frames.length > 5);
  });
```

### TC_52 CSV导出下载闭环

范围：Chromium / browser API fixtures / business mock。结果：PASS。

```javascript
await check(52, 'CSV导出下载闭环', async () => {
    const download = page.waitForEvent('download'); await page.getByRole('link', { name: '导出采样 CSV' }).click();
    const file = await download; assert.match(file.suggestedFilename(), /\.csv$/);
    await file.saveAs(path.join(out, 'browser_download.csv'));
    assert.match(readFileSync(path.join(out, 'browser_download.csv'), 'utf8'), /simulation/);
  });
```
