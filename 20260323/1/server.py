import cowsay, shlex, asyncio, json
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


# список допустимых в игре монстров
def get_monsters():
    return cowsay.list_cows() + ["jgsbat"]


class GameParam():
    def __init__(self):
        self.size = 10          # поле 10x10
        self.monsters = {}      # словарь {"name": ..., "hello": ..., "hp": ...}; ключ - (x, y)
        self.players = {}       # {username: {"x": ..., "y": ...}}  -  координаты каждого пользователя
    
    # перенос на другой край поля (если произошёл выход за границы)
    def wrap(self, coordinate):
        return coordinate % self.size
    
    # добавление нового игрока
    def add_player(self, username):
        if username in self.players:
            return False
        
        self.players[username] = {"x": 0, "y": 0}
        return True
    
    # удаление игрока
    def remove_players(self, username):
        self.players.pop(username, None)
    
    # получение координат игрока
    def get_pos(self, username):
        player = self.players[username]
        return player["x"], player["y"]
    
    # попадание игрока в клетку с монстром
    def encounter(self, x, y):
        monster = self.monsters.get((x, y))

        if monster is None:
            return
        
        # если монстр есть -> печать приветствия
        return { "name": monster["name"], "hello": monster["hello"] }

    # перемещения
    def move(self, username, dx, dy):
        player = self.players[username]

        # серверная команда движения
        player["x"] = self.wrap(player["x"] + dx)
        player["y"] = self.wrap(player["y"] + dy)

        # отправка инф. о перемещении клиенту
        x, y = player["x"], player["y"]
        return x, y, self.encounter(x, y)

    # добавление / перезапись монстра
    def addmon(self, name, hello, hp, x, y):
        # может ли быть такой монстр в игре
        if name not in get_monsters():
            return { "status": "error", "message": "Cannot add unknown monster" }

        # перезапись монстра в клетке
        replaced = (x, y) in self.monsters
        self.monsters[(x, y)] = {"name": name, "hello": hello, "hp": hp}

        # отправка инф. о том, какой монстр теперь в этой клетке
        return { "status": "addmon", "name": name, "hello": hello, "x": x, "y": y, "replaced": replaced }

    # атака на монстра в данной клетке
    def attack(self, username, damage, monster_name=None):
        x, y = self.get_pos(username)
        monster = self.monsters.get(x, y)

        # если монстра нет -> говорим клиенту, что его нет
        if monster is None:
            return { "status": "no_monster", "name": monster_name }
        
        # если клиент ввёл имя монстра, которого нет в этой клетке -> говорим, что такого монстра здесь нет
        if monster_name is not None and monster["name"] != monster_name:
            return { "status": "no_monster", "name": monster_name }
        
        # вычисление и нанос урона
        final_damage = min(damage, monster["hp"])
        monster["hp"] -= final_damage

        died = (monster["hp"] == 0)
        name = monster["name"]

        # смерть монстра
        if died:
            del self.monsters[(x, y)]

        # сообщаем клиенту, какой монстр с каким кол-вом hp остался в клетке
        return { "status": "attack", "name": name, "damage": final_damage,
                 "hp_left": 0 if died else monster['hp'], "died": died }
    
    # разбор командной строки, выполнение нужной команды
    def process_command(self, username, line):
        cmd = shlex.split(line)

        match cmd[0]:
            case "move":
                dx = int(cmd[1])
                dy = int(cmd[2])
                return {"status": "move", "data": self.move(username, dx, dy)}

            case "addmon":
                name = cmd[1]
                hello = cmd[2]
                hp = int(cmd[3])
                x = int(cmd[4])
                y = int(cmd[5])
                return self.addmon(name, hello, hp, x, y)

            case "attack":
                if len(cmd) == 2:
                    damage = int(cmd[1])
                    return self.attack(username, damage)
                else:
                    monster_name = cmd[1]
                    damage = int(cmd[2])
                    return self.attack(username, damage, monster_name)


''' ----- main ----- '''

# объект, хранящий текущее состояние
game = GameParam()
clients = {}                # список игроков

# сообщение одному пользователю
async def sent_to_one(writer, message):
    writer.write((message + "\n").encode())
    await writer.drain()            # await - приостановка

# сообщение всем пользователям
async def send_to_everyone(message):
    dead_clients = []                   # имена пользователей, которые по какой-то причине отключились

    # кидаем сообщение всем подключенным пользователям
    for username, writer in clients.items():
        try:
            writer.write((message + "\n").encode())             # байт-строка отправляется в сокет
        except Exception:
            dead_clients.append(username)
    
    # доотправка сообщений
    for username, writer in clients.items():
        if username not in dead_clients:                        # проверка на случай, если уже решили, что нужно удалить пользователя
            try:
                await writer.drain()
            except Exception:
                dead_clients.append(username)
    
    # удаляем мертвых пользователей
    for username in dead_clients:
        clients.pop(username, None)
        game.remove_players(username)

# обработка подключения клиента
async def MUD(reader, writer):
    '''
    Клиент присылает строку (команду)
    Сервер, в свою очередь:
        1. читает строку
        2. вызывает process_command
        3. преобразовывает ответ в json
        4. отправляет ответ клиенту
    '''
    while data := await reader.readline():
        cmd = data.decode().strip()
        res = game.process_command(cmd)

        response = json.dumps(res) + "\n"
        writer.write(response.encode())
        await writer.drain()

    writer.close()
    await writer.wait_closed()

# локальный сервер на 1337 порту
# клиенту нужно подключаться к 127.0.0.1:1337
async def main():
    server = await asyncio.start_server(MUD, "127.0.0.1", 1337)
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("Server stopped")
