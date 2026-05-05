"""Общие константы для клиент-серверного MUD"""

HOST = "127.0.0.1"
PORT = 1337
MSG_DELIM = "\0"

FIELD_SIZE = 10                     # размер поля

MONSTER_MOVE_INTERVAL = 30          # монстры ходят раз в 30 секунд
SCRIPT_COMMAND_DELAY = 1            # задержка 1 сек между отправками команд с клиента на сервер

# оружие
WEAPONS = {"sword": 10, "spear": 15, "axe": 20}

# перемещения
DIRECTIONS = {
    "right": (1,  0),
    "left":  (-1, 0),
    "up":    (0, -1),
    "down":  (0,  1),
}
