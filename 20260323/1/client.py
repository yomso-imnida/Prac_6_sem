import cmd, shlex, socket, sys, threading
from server import weapons, get_monsters


class cmd_MUD(cmd.Cmd):
    prompt = '>>> '

    def __init__(self, username):
        super().__init__()
        '''
        Клиент не хранит состояние игры. Он:
        - читает команды, отправляет их серверу
        - отдельно получает асинхронные сообщения
        '''
        self.username = username
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(("127.0.0.1", 1337))

        self.alive = True
        self.sock.sendall((self.username + "\n").encode())

        self.receiver = threading.Thread(target=self.receive_loop, daemon=True)
        self.receiver.start()
    
    # отправка одной команды серверу
    def send_line(self, line):
        self.sock.sendall((line + "\n").encode())           # сервер читает команды построчно

    # отдельный поток, который постоянно слушает сервер
    # как только от сервера приходит сообщение -> печатаем его
    def receive_loop(self):
        while self.alive:
            try:
                # читаем очередную порцию данных из сокета
                data = self.sock.recv(1024)
                if not data:
                    # пустые данные -> соединение закрыто
                    break

                # печатаем сообщение сервера
                print()
                print(data.decode(), end="")
                # после асинхронного сообщения заново показываем приглашение к вводу
                print(self.prompt, end="", flush=True)

            except OSError:
                # если сокет уже закрыт -> выходим из цикла
                break

        self.alive = False

    # если есть аргументы у движения - ошибка

    # up -> (0, -1)
    def do_up(self, arg):
        if arg:
            print("Invalid arguments")
            return
        self.send_line("move 0 -1")
    
    # down -> (0, 1)
    def do_down(self, arg):
        if arg:
            print("Invalid arguments")
            return
        self.send_line("move 0 1")
    
    # left -> (-1, 0)
    def do_left(self, arg):
        if arg:
            print("Invalid arguments")
            return
        self.send_line("move -1 0")

    # right -> (1, 0)
    def do_right(self, arg):
        if arg:
            print("Invalid arguments")
            return
        self.send_line("move 1 0")

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

        # про монстра должна быть известна полная информация
        if (hello is None) or (hp is None) or (x is None) or (y is None):
            print("Invalid arguments")
            return

        # quote - чтобы с пробелами нормально обработалось
        request = f"addmon {shlex.quote(name)} {shlex.quote(hello)} {hp} {x} {y}"
        self.send_line(request)
    
    # могут быть команды вида: attack, attack <monster_name>,
    # attack with <weapon>, attack <monster_name> with <weapon>
    def do_attack(self, arg):
        try:
            line_split = shlex.split(arg)
        except ValueError:
            print("Invalid arguments")
            return
        
        monster_name = None
        weapon = "sword"            # по дефолту оружие - sword

        if len(line_split) == 0:
            pass                    # если нет аргементов -> дефолтное оружие sword -> урон 10

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

        self.send_line(request)

    # автодополнение для attack
    def complete_attack(self, text, line, i_begin, i_end):          # text - имя монстра, которое уже начали вводить
        line_split = shlex.split(line[:i_begin])                    # смотрим, какая команда введена (до text)

        if len(line_split) == 1:
            # смотрим на все имена, которые начинаются с text   (после attack)
            return [name for name in get_monsters() if name.startswith(text)]

        if (len(line_split) == 2) and (line_split[0] == "attack") and (line_split[1] == "with"):
            # смотрим на оружие   (после attack with)
            return [name for name in weapons if name.startswith(text)]

        if (len(line_split) == 3) and (line_split[0] == "attack") and (line_split[2] == "with"):
            # смотрим на оружие   (после attack <monster> with)
            return [name for name in weapons if name.startswith(text)]

        return []

    # вызывается, когда неизвестная команда (в старой версии - последний else)
    def default(self, arg):
        print("Invalid command")

    # если будет пустая строка - ничего не делать
    def emptyline(self):
        pass

    # чтобы на ctrl+D программа завершалась
    def do_EOF(self, arg):
        print()
        self.alive = False
        self.sock.close()
        return True


''' ----- main ----- '''

print("<<< Welcome to Python-MUD 0.1 >>>")

# имя пользователя передаётся при запуске клиента
# python3 client.py <username>
if len(sys.argv) != 2:
    print("Usage: python3 client.py <username>")
    raise SystemExit(1)

cmd_MUD(sys.argv[1]).cmdloop()
