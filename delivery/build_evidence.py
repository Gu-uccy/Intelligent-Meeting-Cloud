"""Aggregate observed test outputs; never substitutes a pass for missing evidence."""
import ast
import csv
import hashlib
import json
import re
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'delivery/results'
DOCS = ROOT / 'delivery/docs'


def read_json(name):
    return json.loads((OUT / name).read_text(encoding='utf-8-sig'))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    # Normalize captured terminal logs only; CSV/JSON and screenshots retain their data.
    for log in OUT.glob('*.log'):
        raw = log.read_bytes()
        encoding = 'utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
        content = raw.decode(encoding)
        with log.open('w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(line.rstrip() for line in content.splitlines()).rstrip() + '\n')
    backend = read_json('backend_tests.json')
    browser = read_json('browser_tests.json')
    tests = backend + browser['tests']
    assert len(tests) == 52 and len({t['id'] for t in tests}) == 52, 'Expected 52 distinct executed cases'
    assert {t['id'] for t in tests} == {f'TC_{i:02d}' for i in range(1, 53)}
    shots = list((ROOT / 'delivery/screenshots').glob('*.png'))
    assert len(shots) == 9 and len(browser['screenshots']) == 9, 'Expected nine screenshots'
    assert {p.name for p in shots} == {s['file'] for s in browser['screenshots']}
    source_files = [
        'Flask/unified_meeting_room_system.py',
        'FrontEnd/Intelligent_meeting_cloud/src/views/User/Room3D/index.vue',
        'FrontEnd/Intelligent_meeting_cloud/src/views/User/Booking/components/RoomDetail.vue',
        'FrontEnd/Intelligent_meeting_cloud/src/views/User/Layout/components/LayoutNav.vue',
        'scripts/start-all.ps1', 'scripts/start-backend.ps1',
        'delivery/tests/test_sensor_contract.py', 'delivery/tests/browser_acceptance.mjs',
    ]
    backend_ast = ast.parse((ROOT / source_files[-2]).read_text(encoding='utf-8'))
    methods = {int(n.name.split('_')[1]): n for n in ast.walk(backend_ast)
               if isinstance(n, ast.FunctionDef) and re.match(r'test_\d+_', n.name)}
    browser_source = (ROOT / source_files[-1]).read_text(encoding='utf-8')
    enriched = []
    rows = ['# 52 条可执行测试用例', '',
            '自动从本轮结果和测试源码汇总。TC_01–32 使用 Flask test_client/GPIO 替身；TC_33–52 使用 Chrome、业务 mock、API 夹具，TC_52 实际下载本地模拟 CSV。没有实物通过项。', '',
            '| 编号 | 用例 | 结果 | 源码入口 |', '|---|---|---|---|']
    details = ['', '## 操作与断言', '']
    for item in tests:
        record = dict(item)
        num = int(item['id'].split('_')[1])
        if num <= 32:
            node = methods[num]
            src = source_files[-2]
            line = node.lineno
            procedure = ast.unparse(node)
        else:
            src = source_files[-1]
            match = re.search(rf'  await check\({num},', browser_source)
            assert match, f'Missing source for {num}'
            line = browser_source[:match.start()].count('\n') + 1
            end = browser_source.find('  await check(', match.end())
            if end < 0:
                end = browser_source.index('\n} finally', match.end())
            procedure = browser_source[match.start():end].strip()
        record.update(source=src, line=line, procedure=procedure)
        enriched.append(record)
        rows.append(f"| {item['id']} | {item['name']} | {item['status']} | [{Path(src).name}:{line}](../../{src}#L{line}) |")
        details += [f"### {item['id']} {item['name']}", '', f"范围：{item['scope']}。结果：{item['status']}。", '',
                    '```' + ('python' if num <= 32 else 'javascript'), procedure, '```', '']
    (ROOT / 'delivery/tests/test-cases.md').write_text('\n'.join(rows + details), encoding='utf-8')
    write_json(OUT / 'test-cases.json', enriched)
    with (OUT / 'test-cases.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'name', 'status', 'scope', 'duration_ms', 'source', 'line'])
        writer.writeheader()
        writer.writerows({k: t.get(k, '') for k in writer.fieldnames} for t in enriched)

    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    doc_paths = {p for p in tracked if Path(p).suffix.lower() in {'.md', '.docx', '.pdf'} and (ROOT / p).is_file()
                 and not p.startswith(('delivery/results/', 'delivery/tests/'))}
    doc_paths |= {p.relative_to(ROOT).as_posix() for p in (ROOT / 'delivery').rglob('*.md')
                  if 'results' not in p.parts and 'tests' not in p.parts}
    doc_paths.add('delivery/docs/document-inventory.md')
    doc_paths = sorted(doc_paths)
    inventory = ['# 文档清单', '', f'共 {len(doc_paths)} 份 Markdown/Word/PDF 文件。统计现存 Git 跟踪文件及本交付文档；未跟踪的个人文件、CSV/JSON、截图和视频不计入。数量不代替内容质量或历史报告实测复核。', '',
                 '| 编号 | 文件 |', '|---|---|']
    inventory += [f'| {i} | [{p}](../../{p}) |' for i, p in enumerate(doc_paths, 1)]
    (DOCS / 'document-inventory.md').write_text('\n'.join(inventory) + '\n', encoding='utf-8')

    perf = read_json('api_performance.json')
    frames = list(csv.DictReader((OUT / 'frame_intervals.csv').open(encoding='utf-8-sig')))
    intervals = sorted(float(r['interval_ms']) for r in frames)
    p95 = intervals[min(len(intervals)-1, int(len(intervals)*.95))]
    performance = ['# 性能采样方法与结果', '',
                   f"Flask test_client 连续 {perf['samples']} 次：中位 {perf['median_ms']:.3f} ms，P95 {perf['p95_ms']:.3f} ms。范围为进程内处理，不含网络、反向代理、排队和 GPIO/舵机执行时间。", '',
                   '| 视口 | reload 到场景数据就绪 ms |', '|---|---|']
    performance += [f"| {r['viewport']} | {r['ready_ms']} |" for r in browser['performance']]
    performance += ['', f'Chrome headless requestAnimationFrame 采样 {len(intervals)} 个间隔，中位 {statistics.median(intervals):.3f} ms、P95 {p95:.3f} ms。它不代表现场 GPU 帧率或渲染预算；不可据此宣称 60 FPS。', '',
                    '单次页面样本含本地 Vite dev、刷新及状态等待，机器负载和缓存影响明显；没有真实并发压测、硬件延迟或 SLA 验收。原始 api_performance.csv、browser_performance.csv、frame_intervals.csv 保留便于复算。', '',
                    '生产构建通过，仍有 chunk 大小警告；后续按需分包。没有为通过验收而关闭警告。']
    (DOCS / 'performance-report.md').write_text('\n'.join(performance) + '\n', encoding='utf-8')

    preflight = read_json('preflight.json')
    runtime = read_json('local_runtime.json')
    build = read_json('validation.json')
    failures = [t for t in tests if t['status'] != 'PASS']
    report = ['# 本轮测试与交付报告', '', f"汇总时间：{datetime.now(timezone.utc).isoformat()}。52 条中通过 {52-len(failures)}，失败 {len(failures)}；截图 9 张。", '',
              f"环境：Windows，Chrome {browser['browser']}，Vue/Vite/Three.js；Browser plugin 不可用，使用 Playwright。构建退出码 {build['frontend_build_exit_code']}。", '',
              '## 结果及范围', '',
              '| 项目 | 实际验证 | 结论 |', '|---|---|---|',
              '| TC_01–32 | Flask 隔离、GPIO 替身、非法输入、缺失/过期、导出、双 PWM | 见 backend_tests.json |',
              '| TC_33–52 | 浏览器业务 mock/API 夹具；CSV 下载本地模拟 HTTP | 见 browser_tests.json |',
              f"| Demo 运行 | 前端 HTTP {runtime['frontend_status']}，Flask source={runtime['health']['source']} | 本机演示可用 |",
              f"| Full 预检 | Maven={preflight['maven']}，Redis={preflight['redis_tcp']}，8080空闲={preflight['spring_port_8080_free']}，Pi={preflight['raspberry_sensor']} | 受阻，未跑完整业务链路 |",
              '| 实物执行 | Pi 不可达，无物理 GPIO/机械观察 | 待现场 |', '',
              f"浏览器 pageerror {len(browser['errors'])} 条，console warning {len(browser['warnings'])} 条。生产构建日志另见 build.log（含大包提示）。", '',
              '## 本轮修复', '',
              '- 硬件温湿度不再被模拟环境覆盖；缺失保留 null、过期标识，不阻断门灯返回。',
              '- 舵机失败返回失败并保留指令状态；控制参数校验，门无门磁的限制明确展示。',
              '- 模拟/实时/缺失/断线来源提示、烟雾报警、CSV 下载，预约失败不再显示成功。',
              '- 手机数据面板移到模型下方，导航可横滚；桌面侧栏可滚动，卡片不拆单位。',
              '- 启动预检、识别传感器服务、端口避让和 Maven 多模块启动修正。', '',
              '## 待现场与限制', '',
              '树莓派 192.168.43.206 当前不可达。MySQL TCP 可达不代表数据库权限/业务通过；Maven/Redis 缺失且 8080 占用。52 条不是 52 条硬件或完整后端端到端测试。Blender 脚本保留但本轮未运行原生工具验证。视频按用户要求排除。', '',
              '复测步骤见 ../docs/test-protocol.md；现场填 ../docs/hardware-acceptance.md。旧 week7-8/week9-11 报告为合入远端的历史材料，不计为本轮实测。']
    (OUT / 'test-report.md').write_text('\n'.join(report) + '\n', encoding='utf-8')
    # Recompute inventory after writing generated documentation, including performance report.
    if 'delivery/docs/performance-report.md' not in doc_paths:
        return main()
    files = sorted(p for p in (ROOT / 'delivery').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name != 'manifest.json')
    manifest = {'generated_at': datetime.now(timezone.utc).isoformat(), 'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
                'source_snapshot': 'Working-tree SHA256 at evidence assembly; base_commit is the parent checkout, not a claim that uncommitted sources exist at that commit.',
                'tests': {'total': 52, 'passed': 52-len(failures), 'hardware_tested': False},
                'documents': len(doc_paths), 'screenshots': len(shots),
                'files': {p.relative_to(ROOT).as_posix(): digest(p) for p in files},
                'source_hash_normalization': 'CRLF to LF, matching Git text blobs for Windows source files',
                'source_sha256': {p: hashlib.sha256((ROOT / p).read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in source_files}}
    write_json(OUT / 'manifest.json', manifest)
    print(json.dumps({k: manifest[k] for k in ['tests', 'documents', 'screenshots']}, ensure_ascii=False))
    if failures or build['frontend_build_exit_code'] != 0:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
