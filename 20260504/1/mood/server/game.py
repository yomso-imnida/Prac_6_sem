"""Обработка состояния игры и команд для MUD-сервера."""

import random
import cowsay
import shlex
from importlib import resources

# словарь с оружием для нанесения урона монстру
from mood.common.constants import WEAPONS, FIELD_SIZE, DIRECTIONS

def load_jgsbat():
    """Загрузка летучей мыши (монстра jgsbat) из файла jgsbat.txt."""
    cow_path = resources.files("mood.server").joinpath("data/jgsbat.txt")

    with cow_path.open(encoding="utf-8") as cow_file:
        return cowsay.read_dot_cow(cow_file)


JGSBAT = load_jgsbat()


def get_monsters():
    """Список допустимых в игре монстров."""
    return cowsay.list_cows() + ["jgsbat"]


def make_cowsay_message(encounter):
    """Формирование многострочного приветствие монстра в формате cowsay (для jgsbat используется спец-cowfile)."""
    if encounter["name"] == "jgsbat":
        return cowsay.cowsay(encounter["hello"], cowfile=JGSBAT)
    return cowsay.cowsay(encounter["hello"], cow=encounter["name"])


class GameParam():
    """Состояния игрового поля, игроков, монстров."""

    def __init__(self):
        """Создание начального, пустого состояния игры."""
        self.size = FIELD_SIZE      # поле 10x10
        self.monsters = {}          # словарь {"name": ..., "hello": ..., "hp": ...}; ключ - (x, y)
        self.players = {}           # {username: {"x": ..., "y": ...}}  -  координаты каждого пользователя
        self.moving_monsters = True         # фрежим бродячих монстров по умолчанию включен

    def wrap(self, coordinate):
        """Если произошёл выход за границы, то перенос на другой край поля."""
        return coordinate % self.size

    def add_player(self, username):
        """Добавление нового игрока."""
        if username in self.players:
            return False

        self.players[username] = {"x": 0, "y": 0}
        return True

    def remove_player(self, username):
        """Удаление игрока."""
        self.players.pop(username, None)

    def set_movemonsters(self, val):
        """Включение / выключение режима бродячих монстров."""
        self.moving_monsters = val
        return {
            "status": "movemonsters",
            "enabled": self.moving_monsters,
        }

    def get_pos(self, username):
        """Получение координат игрока."""
        player = self.players[username]
        return player["x"], player["y"]

    def encounter(self, x, y):
        """Если в клетке есть монстр, то получение данных о монстре."""
        monster = self.monsters.get((x, y))

        if monster is None:
            return

        # если монстр есть -> печать приветствия
        return {
            "name": monster["name"],
            "hello": monster["hello"]
        }

    def players_at(self, x, y):
        """Получение имен всех игроков, которые находятся в этой клеточке."""
        # нужны все игроки, тк на одной клетке может стоять несколько пользователей
        return [
            username
            for username, player in self.players.items()
            if player["x"] == x and player["y"] == y
        ]

    def move_random_monster(self):
        """Перемещение случайного монстра на одну клетку в случайном направлении."""
        # если монстров нет
        if not self.monsters:
            return None

        while True:
            # выбор случайного монстра
            old_pos, monster = random.choice(list(self.monsters.items()))
            # выбор случайного направления
            direction, delta = random.choice(list(DIRECTIONS.items()))

            old_x, old_y = old_pos
            dx, dy = delta
            new_pos = (self.wrap(old_x + dx), self.wrap(old_y + dy))

            # если клетка занята -> монстр и направление выбираются заново
            if new_pos in self.monsters:
                continue

            self.monsters[new_pos] = monster
            del self.monsters[old_pos]

            x, y = new_pos

            return {
                "name": monster["name"],
                "direction": direction,
                "x": x,
                "y": y,
                "encounter": self.encounter(x, y),
                "players": self.players_at(x, y),               # если есть игроки на клетке - тоже сообщаем об этом
            }

    def move(self, username, dx, dy):
        """Перемещение игрока по полю с учётом циклического выхода за границы."""
        player = self.players[username]

        # серверная команда движения
        player["x"] = self.wrap(player["x"] + dx)
        player["y"] = self.wrap(player["y"] + dy)

        # отправка инфs о перемещении клиенту
        x, y = player["x"], player["y"]
        return x, y, self.encounter(x, y)

    def addmon(self, name, hello, hp, x, y):
        """Добавление или перезапись монстра."""
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
        """Атака монстра в текущей клетке игрока; если имя монстра задано, то проверка, что имя существует."""
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
        final_damage = min(damage, monster["hp"])           # нельзя снять больше hp, чем осталось у монстра
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
        """Разбор и выполнение одной команды клиента."""
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

                case "movemonsters":
                    if len(cmd) != 2:
                        return {"status": "error", "message": "Invalid arguments"}

                    match cmd[1]:
                        case "on":
                            return self.set_movemonsters(True)

                        case "off":
                            return self.set_movemonsters(False)

                        case _:
                            return {"status": "error", "message": "Invalid arguments"}

                case "locale":
                    if len(cmd) != 2:
                        return {"status": "error", "message": "Invalid arguments"}
                    return {"status": "locale", "locale": cmd[1]}

                case _:
                    return {"status": "error", "message": "Invalid command"}

        except ValueError:
            return {"status": "error", "message": "Invalid arguments"}
