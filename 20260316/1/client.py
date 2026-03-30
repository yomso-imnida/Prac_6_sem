import cmd, shlex, cowsay, socket, json
from io import StringIO
from server import weapons, get_monsters

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

class cmd_MUD(cmd.Cmd):
    prompt = '>>> '

    def __init__(self):
        cmd.Cmd.__init__(self)

        # в клиенте больше не хранится состояние игры; он просто подключается к серверу, и происходит обмен командами
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("127.0.0.1", 1337))
        self.socket_file = self.sock.makefile("r")

    def print_res(self, res):
        match res['status']:
            case "moved":
                print(f"Moved to ({res['x']}, {res['y']})")

                enc = res["encounter"]
                if enc is not None:
                    if enc["name"] == "jgsbat":
                        print(cowsay.cowsay(enc['hello'], cowfile=jgsbat))
                    else:
                        print(cowsay.cowsay(enc['hello'], cow=enc['name']))
            
            case "addmon":
                print(f"Added monster {res['name']} to ({res['x']}, {res['y']}) saying {res['hello']}")

                if res["replaced"]:
                    print("Replaced the old monster")

            case "no_monster":
                if res['name'] is None:
                    print("No monster here")
                else:
                    print(f"No {res['name']} here")

            case "attack":
                print(f"Attacked {res['name']}, damage {res['damage']} hp")

                if res["died"]:
                    print(f"{res['name']} died")
                else:
                    print(f"{res['name']} now has {res['hp_left']}")

            case "error":
                print(res['message'])

    # отправляется строка с командой; ответ - это json-строка
    def send_request(self, line):
        self.sock.sendall((line + "\n").encode())           # sendall - отправка всех данных
        return json.loads(self.socket_file.readline())

    # если есть аргументы у движения - ошибка

    def do_up(self, arg):
        if arg:
            print("Invalid arguments")
            return
        self.print_res(self.send_request("move 0 -1"))
    
    def do_down(self, arg):
        if arg:
            print("Invalid arguments")
            return
        self.print_res(self.send_request("move 0 1"))
        
    def do_left(self, arg):
        if arg:
            print("Invalid arguments")
            return
        self.print_res(self.send_request("move -1 0"))

    def do_right(self, arg):
        if arg:
            print("Invalid arguments")
            return
        self.print_res(self.send_request("move 1 0"))

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

        request = f"addmon {shlex.quote(name)} {shlex.quote(hello)} {hp} {x} {y}"
        self.print_res(self.send_request(request))
    
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

        damage = weapons[weapon]

        if monster_name is None:
            request = f"attack {damage}"
        else:
            request = f"attack {shlex.quote(monster_name)} {damage}"

        self.print_res(self.send_request(request))

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
        self.socket_file.close()
        self.sock.close()
        return True


''' ----- main ----- '''

print("<<< Welcome to Python-MUD 0.1 >>>")

cmd_MUD().cmdloop()
