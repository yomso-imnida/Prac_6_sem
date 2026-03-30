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
        
        return { "name": monster["name"], "hello": monster["hello"] }

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
        
        return { "status": "moved", "x": self.tmp_x, "y": self.tmp_y, "encounter": self.encounter(self.tmp_x, self.tmp_y) }

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
