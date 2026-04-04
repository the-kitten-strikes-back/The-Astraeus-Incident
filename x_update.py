import os

root='fps_game'
py_files=[]
for dirpath, dirnames, filenames in os.walk(root):
    dirnames.sort()
    for fn in sorted(filenames):
        if fn.endswith('.py'):
            py_files.append(os.path.join(dirpath, fn))

with open('x.md','w',encoding='utf-8') as f:
    f.write('# fps_game Code (All .py Files)\n\n')
    for path in py_files:
        f.write(f'## {path}\n')
        f.write(f'Filename: `{path}`\n\n')
        f.write('```python\n')
        try:
            with open(path,'r',encoding='utf-8') as pf:
                f.write(pf.read().rstrip())
        except UnicodeDecodeError:
            with open(path,'r',encoding='latin-1') as pf:
                f.write(pf.read().rstrip())
        f.write('\n```\n\n')