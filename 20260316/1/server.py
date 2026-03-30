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
        
        return { "name": monster["name"], "hello": monster["hello"] }

    # перемещения
    def move(self, dx, dy):
        # серверная команда движения:
        self.tmp_x = self.wrap(self.tmp_x + dx)
        self.tmp_y = self.wrap(self.tmp_y + dy)

        return {
            "status": "moved",
            "x": self.tmp_x,
            "y": self.tmp_y,
            "encounter": self.encounter(self.tmp_x, self.tmp_y)
        }

    # добавление / перезапись монстра
    def addmon(self, name, hello, hp, x, y):
        if name not in get_monsters():
            return { "status": "error", "message": "Cannot add unknown monster" }

        replaced = (x, y) in self.monsters
        self.monsters[(x, y)] = {"name": name, "hello": hello, "hp": hp}
        
        return { "status": "addmon", "name": name, "hello": hello, "x": x, "y": y, "replaced": replaced }

    def attack(self, damage, monster_name=None):
        monster = self.monsters.get((self.tmp_x, self.tmp_y))

        if monster is None:
            return { "status": "no_monster", "name": monster_name }
        
        if monster_name is not None and monster["name"] != monster_name:
            return { "status": "no_monster", "name": monster_name }
        
        # вычисление и нанос урона
        final_damage = min(damage, monster["hp"])
        monster["hp"] -= final_damage

        died = (monster["hp"] == 0)
        name = monster["name"]

        if died:
            del self.monsters[(self.tmp_x, self.tmp_y)]

        return { "status": "attack", "name": name, "damage": final_damage,
                 "hp_left": 0 if died else monster['hp'], "died": died }
    
    def process_command(self, line):
        cmd = shlex.split(line)

        match cmd[0]:
            case "move":
                dx = int(cmd[1])
                dy = int(cmd[2])
                return self.move(dx, dy)

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
                    return self.attack(damage)
                else:
                    monster_name = cmd[1]
                    damage = int(cmd[2])
                    return self.attack(damage, monster_name)


# объект, хранящий текущее состояние
game = GameParam

async def MUD(reader, writer):
    while data := await reader.readline():
        cmd = data.decode().strip()
        res = game.process_command(cmd)

        response = json.dumps(res) + "\n"
        writer.write(response.encode())
        await writer.drain()

    writer.close()
    await writer.wait_closed()


''' ----- main ----- '''

# локальный сервер на 1337 порту
async def main():
    server = await asyncio.start_server(MUD, "127.0.0.1", 1337)
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
