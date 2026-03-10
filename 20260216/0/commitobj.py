import sys
from pathlib import Path
import zlib

for obj in Path(sys.argv[1]).glob(".git/objects/??/*"):
    print(obj)
    data = zlib.decompress(obj.read_bytes())
    head, _, tail = data.partition(b'\x00')         # partition() делит bytes по первому вхождению разделителя
                                                    # head — всё до \x00, _ — сам разделитель, tail — всё после \x00
    kind, size = head.split()
    match kind.decode():                            # kind.decode() превращает bytes -> str: было b"commit", стало "commit"
        case 'commit':
            print(tail.decode())                    # печать текста коммита

# python commitobj.py /home/StarPurpleDust/Documents/C/6_sem/Prac/
