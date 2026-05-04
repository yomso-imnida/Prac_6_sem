""" Game state and command processing for MUD-server """

import cowsay
import shlex
from io import StringIO

# словарь с оружием для нанесения урона монстру
from mood.common.constants import WEAPONS

JGSBAT = cowsay.read_dot_cow(StringIO(r"""
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

def get_monsters():
    """ список допустимых в игре монстров """
    return cowsay.list_cows() + ["jgsbat"]

def make_cowsay_message(encounter):
    """
    формируем многострочное приветствие монстра в формате cowsay
    для jgsbat используем специальный cowfile
    """
    if encounter["name"] == "jgsbat":
        return cowsay.cowsay(encounter["hello"], cowfile=JGSBAT)
    return cowsay.cowsay(encounter["hello"], cow=encounter["name"])


class GameParam():
    """ состояния игрового поля, игроков, монстров """

    def __init__(self):
        """ создание начального, пустого состояния игры """
        self.size = 10          # поле 10x10
        self.monsters = {}      # словарь {"name": ..., "hello": ..., "hp": ...}; ключ - (x, y)
        self.players = {}       # {username: {"x": ..., "y": ...}}  -  координаты каждого пользователя

    def wrap(self, coordinate):
        """ если произошёл выход за границы -> перенос на другой край поля """
        return coordinate % self.size

    def add_player(self, username):
        """ добавление нового игрока """
        if username in self.players:
            return False

        self.players[username] = {"x": 0, "y": 0}
        return True

    def remove_player(self, username):
        """ удаление игрока """
        self.players.pop(username, None)

    def get_pos(self, username):
        """ получение координат игрока """
        player = self.players[username]
        return player["x"], player["y"]

    def encounter(self, x, y):
        """ если в клетке есть монстр -> получение данных о монстре """
        monster = self.monsters.get((x, y))

        if monster is None:
            return

        # если монстр есть -> печать приветствия
        return {
            "name": monster["name"],
            "hello": monster["hello"]
        }

    def move(self, username, dx, dy):
        """ перемещение игрока по полю с учётом циклического выхода за границы """
        player = self.players[username]

        # серверная команда движения
        player["x"] = self.wrap(player["x"] + dx)
        player["y"] = self.wrap(player["y"] + dy)

        # отправка инфs о перемещении клиенту
        x, y = player["x"], player["y"]
        return x, y, self.encounter(x, y)

    def addmon(self, name, hello, hp, x, y):
        """ добавление или перезапись монстра """

        # может ли быть такой монстр в игре
        if name not in get_monsters():
            return {
                "status": "error",
                "message": "Cannot add unknown monster"
            }

        # перезапись монстра в клетке
        replaced = (x, y) in self.monsters
        self.monsters[(x, y)] = {"name": name, "hello": hello, "hp": hp}

        # отправка инф. о том, какой монстр теперь в этой клетке
        return {
            "status": "addmon",
            "name": name,
            "hello": hello,
            "hp": hp,
            "x": x,
            "y": y,
            "replaced": replaced
        }

    def attack(self, username, weapon, monster_name=None):
        """ атака монстра в текущей клетке игрока. если имя монстра задано -> проверяем, что имя существует """
        if weapon not in WEAPONS:
            return {
                "status": "error",
                "message": "Unknown weapon"
            }

        x, y = self.get_pos(username)
        monster = self.monsters.get((x, y))

        # в клеточке нет монстра
        if monster is None:
            return {
                "status": "no_monster",
                "name": monster_name
            }

        # в клеточке есть монстр, но не тот, которого написал пользователь
        if monster_name is not None and monster["name"] != monster_name:
            return {
                "status": "no_monster",
                "name": monster_name
            }

        damage = WEAPONS[weapon]
        final_damage = min(damage, monster["hp"])
        monster["hp"] -= final_damage

        died = monster["hp"] == 0
        name = monster["name"]

        # если hp закончились -> убираем монстра из клетки
        if died:
            del self.monsters[(x, y)]

        return {
            "status": "attack",
            "name": name,
            "weapon": weapon,
            "damage": final_damage,
            "hp_left": 0 if died else monster["hp"],
            "died": died,
        }

    def process_command(self, username, line):
        """ разбор и выполнение одной команды клиента """
        if username not in self.players:
            return {
                "status": "error",
                "message": "Player is not connected"
            }

        try:
            cmd = shlex.split(line)
        except ValueError:
            return {
                "status": "error",
                "message": "Invalid arguments"
            }

        if not cmd:
            return {"status": "error", "message": "Invalid command"}

        try:
            match cmd[0]:
                case "move":
                    if len(cmd) != 3:
                        return {"status": "error", "message": "Invalid arguments"}
                    dx = int(cmd[1])
                    dy = int(cmd[2])
                    return {"status": "move", "data": self.move(username, dx, dy)}

                case "addmon":
                    if len(cmd) != 6:
                        return {"status": "error", "message": "Invalid arguments"}
                    name = cmd[1]
                    hello = cmd[2]
                    hp = int(cmd[3])
                    x = int(cmd[4])
                    y = int(cmd[5])
                    return self.addmon(name, hello, hp, x, y)

                case "attack":
                    if len(cmd) == 2:
                        weapon = cmd[1]
                        return self.attack(username, weapon)
                    if len(cmd) == 3:
                        monster_name = cmd[1]
                        weapon = cmd[2]
                        return self.attack(username, weapon, monster_name)
                    return {"status": "error", "message": "Invalid arguments"}

                case "sayall":
                    if len(cmd) != 2:
                        return {"status": "error", "message": "Invalid arguments"}
                    return {"status": "sayall", "message": cmd[1]}

                case _:
                    return {"status": "error", "message": "Invalid command"}
        except ValueError:
            return {"status": "error", "message": "Invalid arguments"}
