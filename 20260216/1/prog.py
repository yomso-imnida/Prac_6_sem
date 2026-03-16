import sys, os, zlib

# печать списка веток
def heads_list():
    # ветки лежат в .git/refs/heads/
    path_heads = sys.argv[1] + "/.git/refs/heads/"
    
    for name in os.listdir(path_heads):
        print(name)

# нахождение последнего коммита
# id коммита лежит в .git/refs/heads/branch
def commit_branch(branch):
    path_branch = sys.argv[1] + "/.git/refs/heads/" + branch

    file = open(path_branch)
    sha = file.read().strip()

    file.close()

    return sha

# нахождение объекта-дерева последнего коммита
# объекты лежат в .git/objects/xx/yyyy
def find_obj(sha):
    path = (sys.argv[1] + "/.git/objects/" + sha[:2] + "/" + sha[2:])

    bytes_data = open(path, "rb").read()
    data = zlib.decompress(bytes_data)
    head, _, tail = data.partition(b'\x00')         # partition() делит bytes по первому вхождению разделителя
                                                    # head - всё до \x00, _ - сам разделитель, tail - всё после \x00

    obj_type = head.split(b" ")[0].decode()         # разбиваем, берем тип, декодируем

    return obj_type, tail                           # возврат типа git-объекта и его содержимого

# нахождение хэшей: дерева и родительского коммита
def commit_tree(body):
    com_tree, parent_com = None, None

    for line in body.splitlines():
        # хэш дерева
        if line.startswith(b'tree '):
            com_tree = line[5:].decode()

        # хэш родительского коммита
        elif (line.startswith(b'parent ') and parent_com is None):
            parent_com = line[7:].decode()

        # начинается сообщение
        elif line == b'':
            break
    return com_tree, parent_com

# печать дерева
def print_tree(sha):
    type_obj, body_obj = find_obj(sha)

    while body_obj:
    # mode name\x00sha tail
        mode, _, tail = body_obj.partition(b' ')        # partition() - разделяет на ровно три части (часть, разделитель, часть)
        name, _, tail = tail.partition(b'\x00')

        sha = tail[:20].hex()
        body_obj = tail[20:]

        if mode == b'40000':
            type_obj = 'tree'
        else:
            type_obj = 'blob'
        
        print(type_obj, sha, name.decode())


''' ----- main ----- '''

# ввели только путь к каталогу
if len(sys.argv) == 2:
    heads_list()
    sys.exit(0)

# ввели путь к каталогу и имя ветки
if len(sys.argv) != 3:
    sys.exit(1)

# вывод последнего коммита
last_com = commit_branch(sys.argv[2])
type_obj, body_obj = find_obj(last_com)
if type_obj != 'commit':
    sys.exit(1)

print(body_obj.decode())

# вывод tree
sha_tree, parent = commit_tree(body_obj)
print_tree(sha_tree)

# печать с TREE
cur = last_com
while True:
    type_obj, body_obj = find_obj(cur)
    sha_tree, parent = commit_tree(body_obj)

    print("TREE for commit", cur)
    print_tree(sha_tree)

    if parent is None:
        break

    cur = parent
