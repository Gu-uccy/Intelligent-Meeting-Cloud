with open(r'd:\Flask\chapter8\smart_climate_controller.py', encoding='utf-8') as f:
    content = f.read()

start = content.find("html_content = '''")
start = content.index("<!DOCTYPE", start)
end = content.index("</html>'''", start) + len("</html>")

html = content[start:end]

with open(r'd:\Flask\chapter8\templates\index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'HTML模板已写入 ({len(html)} 字符)')
