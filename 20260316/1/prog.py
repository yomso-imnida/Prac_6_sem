import cmd, shlex
import cowsay
from io import StringIO

jgsbat = cowsay.read_dot_cow(StringIO(r"""
$the_cow = <<EOC;
 ,_                    _,
 ) '-._  ,_    _,  _.-' (
 )  _.-'.|\\--//|.'-._  (
  )'   .'\/o\/o\/'.   `(
   ) .' . \====/ . '. (
    )  / <<    >> \  (
     '-._/``  ``\_.-'
jgs     __\\'--'//__
       (((""`  `"")))
EOC
"""))

# словарь с оружием для нанесения урона монстру
weapons = {"sword": 10, "spear": 15, "axe": 20}

# список монстров в игре
def get_monsters():
    return cowsay.list_cows() + ["jgsbat"]


class GameParam():
    def __init__(self):
        self.size = 10          # поле 10x10
        self.tmp_x = 0          # старт игрока в (0, 0)
        self.tmp_y = 0
        self.monsters = {}      # словарь {"name": ..., "hello": ..., "hp": ...}
    
    # перенос на другой край поля (если произошёл выход за границы)
    def wrap(self, coordinate):
        return coordinate % self.size
    
    # попадание игрока в клетку с монстром
    def encounter(self, x, y):
        monster = self.monsters.get((x, y))

        # если монстр есть -> печать приветствия
        if monster is None:
            return
        
        if monster["name"] == "jgsbat":
            print(cowsay.cowsay(monster["hello"], cowfile=jgsbat))
        else:
            print(cowsay.cowsay(monster["hello"], cow=monster["name"]))

    # перемещения
    def movements(self, command):
        match command:
            case "up":
                self.tmp_y = self.wrap(self.tmp_y - 1)
            case "down":
                self.tmp_y = self.wrap(self.tmp_y + 1)
            case "left":
                self.tmp_x = self.wrap(self.tmp_x - 1)
            case "right":
                self.tmp_x = self.wrap(self.tmp_x + 1)
        
        print(f"Moved to {self.tmp_x, self.tmp_y}")
        self.encounter(self.tmp_x, self.tmp_y)              # проверка на "происшествие"
    
    # добавление / перезапись монстра
    def addmon(self, name, hello, hp, x, y):
        if name not in cowsay.list_cows() and name != "jgsbat":
            print("Cannot add unknown monster")
            return

        replaced = (x, y) in self.monsters
        self.monsters[(x, y)] = {"name": name, "hello": hello, "hp": hp}
        print(f"Added monster {name} to ({x}, {y}) saying {hello}")

        if replaced:
            print("Replaced the old monster")

    def attack(self, damage, monster_name=None):

        monster = self.monsters.get((self.tmp_x, self.tmp_y))

        if monster is None:
            if monster_name is None:
                print("No monster here")
            else:
                print(f"No {monster_name} here")
            return
        if monster_name is not None and monster["name"] != monster_name:
            print(f"No {monster_name} here")
            return

        # вычисление урона
        damage = min(damage, monster['hp'])
        print(f"Attacked {monster['name']}, damage {damage} hp")

        # наносим урон монстру
        monster['hp'] -= damage

        # либо убиваем монстра, либо выводим его hp
        if monster['hp'] == 0:
            print(f"{monster['name']} died")
            del self.monsters[(self.tmp_x, self.tmp_y)]
        else:
            print(f"{monster['name']} now has {monster['hp']}")


class cmd_MUD(cmd.Cmd):
    prompt = '>>> '

    def __init__(self):
        cmd.Cmd.__init__(self)
        self.game = GameParam()

    # если есть аргументы у движения - ошибка

    def do_up(self, arg):
        if arg:
            print("Invalid arguments")
            return
        self.game.movements("up")
    
    def do_down(self, arg):
        if arg:
            print("Invalid arguments")
            return
        self.game.movements("down")
        
    def do_left(self, arg):
        if arg:
            print("Invalid arguments")
            return
        self.game.movements("left")

    def do_right(self, arg):
        if arg:
            print("Invalid arguments")
            return
        self.game.movements("right")

    def do_addmon(self, arg):
        try:
            line_split = shlex.split(arg)
        except ValueError:
            print("Invalid arguments")
            return

        if len(line_split) < 1:
            print("Invalid arguments")
            return

        # преобразовываем координаты
        name = line_split[0]            # имя монстра
        hello, hp = None, None
        x, y = None, None

        i = 1
        flag = False                    # для ошибок

        while i < len(line_split):
            match line_split[i]:
                # ----- hello -----
                case "hello":
                    if (i+1) >= len(line_split):
                        print("Invalid arguments")
                        flag = True
                        break
                    hello = line_split[i+1]
                    i += 2

                # ----- hp -----
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

                # ----- coords -----
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

                # ----- other -----
                case _:
                    print("Invalid arguments")
                    flag = True
                    break

        if flag:
            return

        if (hello is None) or (hp is None) or (x is None) or (y is None):
            print("Invalid arguments")
            return

        self.game.addmon(name, hello, hp, x, y)
    
    def do_attack(self, arg):
        try:
            line_split = shlex.split(arg)
        except ValueError:
            print("Invalid arguments")
            return
        
        monster_name = None
        weapon = "sword"

        if len(line_split) == 0:
            pass    # если нет аргементов -> по дефолту урон 10, т.е. оружие - sword
        elif len(line_split) == 1:
            if line_split[0] == "with":
                print("Invalid arguments")
                return
            monster_name = line_split[0]
        elif len(line_split) == 2 and line_split[0] == "with":
            weapon = line_split[1]
        elif len(line_split) == 3 and line_split[1] == "with":
            monster_name = line_split[0]
            weapon = line_split[2]
        else:
            print("Invalid arguments")
            return

        if weapon not in weapons:
            print("Unknown weapon")
            return

        self.game.attack(weapons[weapon], monster_name)

    # text - имя монстра, которое уже начали вводить
    def complete_attack(self, text, line, i_begin, i_end):
        line_split = shlex.split(line[:i_begin])        # смотрим, какая команда введена (до text)

        if len(line_split) == 1:
            # смотрим на все имена, которые начинаются с text
            return [name for name in get_monsters() if name.startswith(text)]

        if (len(line_split) == 2) and (line_split[0] == "attack") and (line_split[1] == "with"):
            return [name for name in weapons if name.startswith(text)]

        if (len(line_split) == 3) and (line_split[0] == "attack") and (line_split[2] == "with"):
            return [name for name in weapons if name.startswith(text)]

        return []

    # вызывается, когда неизвестная команда (в старой версии - последний else)
    def default(self, arg):
        print("Invalid command")

    # если будет пустая строка - ничего не делать
    def emptyline(self):
        pass

    def do_EOF(self, arg):
        print()
        return True


''' ----- main ----- '''

print("<<< Welcome to Python-MUD 0.1 >>>")

cmd_MUD().cmdloop()
