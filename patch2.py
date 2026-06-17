import sys

from patch_ui import new_html

with open('server.py', 'r', encoding='utf-8') as f:
    content = f.read()

parts = content.split('DASHBOARD_HTML = r"""<!DOCTYPE html>')
head = parts[0]

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(head + 'DASHBOARD_HTML = r"""' + new_html + '"""\n')
