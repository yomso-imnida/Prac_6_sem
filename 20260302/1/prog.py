import sys
from cowsay import cowsay, list_cows, read_dot_cow

SIZE = 10               # поле 10x10
tmp_x, tmp_y = 0, 0     # старт игрока в (0, 0)
monsters = {}           # словарь {"name": ..., "hello": ..., "hp": ...}

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

# addmon <monster_name> hello <hello_string> hp <hitpoints> coords <x> <y>

for in_line in sys.stdin:
    line = in_line.strip()

    # пропуск пустых строк
    if not line:
        continue

    # line_split[0] - addmon, ine_split[1] - имя монстра, остальное - в рандомном порядке
    try:
        line_split = shlex.split(line)
    except ValueError:
        print("Invalid arguments")
        continue

    if not line_split:
        continue

    cmd = line_split[0]                 # команда

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
        if len(line_split) < 2:
            print("Invalid arguments")
            continue

        # преобразовываем координаты
        name = line_split[1]        # имя монстра
        hello, hp = None, None
        x, y = None, None

        i = 2
        flag = False                # для ошибок

        while i < len(line_split):
            match line_split[i]:
                case "hello":
                    if (i+1) >= len(line_split):
                        print("Invalid arguments")
                        flag = True
                        break
                    hello = line_split[i+1]
                    i += 2

                case "hp":
                    if (i+1) >= len(line_split):
                        print("Invalid arguments")
                        flag = True
                        break
                    try:
                        hp = int(line_split[i+1])
                    except ValueError:
                        print("Invalid arguments")
                        flag = True
                        break
                    if hp <= 0:
                        print("Invalid arguments")
                        flag = True
                        break
                    i += 2

                case "coords":
                    if (i+2) >= len(line_split):
                        print("Invalid arguments")
                        flag = True
                        break
                    try:
                        x = int(line_split[i+1])
                        y = int(line_split[i+2])
                    except ValueError:
                        print("Invalid arguments")
                        flag = True
                        break
                    i += 3

                case _:
                    print("Invalid arguments")
                    flag = True
                    break

        if (hello is None) or (hp is None) or (x is None) or (y is None):
            print("Invalid arguments")
            continue

        name = line_split[1]                # имя монстра

        if flag:
            continue

        if name not in list_cows() and name != "jgsbat":
            print("Cannot add unknown monster")
            continue

        replaced = (x, y) in monsters
        monsters[(x, y)] = {"name": name, "hello": hello, "hp": hp}
        print(f"Added monster {name} to ({x}, {y}) saying {hello}")

        if replaced:
            print("Replaced the old monster")

    else:
        print("Invalid command")
