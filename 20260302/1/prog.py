import sys
from cowsay import cowsay, list_cows, read_dot_cow

SIZE = 10               # поле 10x10
tmp_x, tmp_y = 0, 0     # старт игрока в (0, 0)
monsters = {}           # словарь {"name": ..., "hello": ...}

jgsbat = read_dot_cow(r"""
    ,_                    _,
    ) '-._  ,_    _,  _.-' (
    )  _.-'.|\\--//|.'-._  (
     )'   .'\/o\/o\/'.   `(
      ) .' . \====/ . '. (
       )  / <<    >> \  (
        '-._/``  ``\_.-'
  jgs     __\\'--'//__
         (((""`  `"")))
""")


# перенос на другой край поля (если произошёл выход за границы)
def wrap(coordinate):
    return coordinate % SIZE

# попадание игрока в клетку с монстром
def encounter(x, y):
    monster = monsters.get((x, y))

    # если монстр есть -> печать приветствия
    if monster is None:
        return
    
    if monster["name"] == "jgsbat":
        print(cowsay(monster["hello"], cowfile=jgsbat))
    else:
        print(cowsay(monster["hello"], cow=monster["name"]))


''' ----- main ----- '''

print("<<< Welcome to Python-MUD 0.1 >>>")

for in_line in sys.stdin:
    line = in_line.strip()

    # пропуск пустых строк
    if not line:
        continue

    line_split = shlex.split(line)       # line_split[0] - команда, остальное - аргументы

    cmd = line_split[0]             # команда

    if cmd in ["up", "down", "left", "right"]:
        # если есть аргументы у движения - ошибка
        if len(line_split) != 1:
            print("Invalid arguments")
            continue

        # само движение
        elif cmd == "up":
            tmp_y = wrap(tmp_y - 1)
        elif cmd == "down":
            tmp_y = wrap(tmp_y + 1)
        elif cmd == "left":
            tmp_x = wrap(tmp_x - 1)
        else:                           # cmd == "right"
            tmp_x = wrap(tmp_x + 1)
        
        print(f"Moved to {tmp_x, tmp_y}")
        encounter(tmp_x, tmp_y)                 # проверка на "происшествие"

    # добавляем монстра
    elif cmd == "addmon":
        # если аргумента не четыре - ошибка
        if len(line_split) != 5:
            print("Invalid arguments")
            continue

        # преобразовываем координаты
        try:
            x = int(line_split[2])
            y = int(line_split[3])
        except ValueError:
            print("Invalid arguments")
            continue

        name = line_split[1]                # имя монстра
        if name not in list_cows() and name != "jgsbat":
            print("Cannot add unknown monster")
            continue
        
        hello = line_split[4]               # привествие монстра
        replaced = (x, y) in monsters       # проверка: есть ли монстр
        monsters[(x, y)] = {"name": name, "hello": hello}            # добавление/замена монстра
        print(f"Added monster {name} to ({x}, {y}) saying {hello}")

        # если монстр уже был - говорим, что произошла замена
        if replaced:
            print("Replaced the old monster")

    else:
        print("Invalid command")
