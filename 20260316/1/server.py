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
