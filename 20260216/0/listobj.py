import sys
from pathlib import Path

# sys.argv[1] - путь к репозиторию
# glob(".git/objects/??/*") - все файлы объектов git
for obj in Path(sys.argv[1]).glob(".git/objects/??/*"):
    print(obj)

# python listobj.py /home/StarPurpleDust/Documents/C/6_sem/Prac/
