import sys
from pathlib import Path
import zlib

# читаем файл объекта как bytes
# распаковываем (т.к. git хранит сжатые объекты)
data = zlib.decompress(Path(sys.argv[1]).read_bytes())
print(data)

# python readobj.py /home/StarPurpleDust/Documents/C/6_sem/Prac/.git/objects/5a/6d1.....
