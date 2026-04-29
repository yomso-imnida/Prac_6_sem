import cmd, shlex, socket, sys, threading, readline
import cowsay

HOST = "127.0.0.1"
PORT = 1337
MSG_DELIM = "\0"
weapons = {"sword": 10, "spear": 15, "axe": 20}


def get_monsters():
    return cowsay.list_cows() + ["jgsbat"]

class cmd_MUD(cmd.Cmd):
    prompt = ">>> "

    '''
        Клиент не хранит состояние игры. Он:
        - читает команды, отправляет их серверу
        - отдельно получает асинхронные сообщения
    '''
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        self.alive = True
        self.recv_buffer = ""           # буфер для частично полученных сообщений 

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))

        # отправляем имя пользователя
        self.sock.sendall((self.username + "\n").encode())

        # первое сообщение: либо успешное подключение, либо отказ

        reply = self.read_message()

        if reply != f"Welcome, {self.username}":
            if reply is not None:
                print(reply)
            else:
                print("Connection closed by server")
            self.close_connection()
            raise SystemExit(1)

        print(reply)

        # после успешного подключения запускаем поток для асинхронного чтения сообщений от сервера
        self.receiver = threading.Thread(target=self.receive_loop, daemon=True)
        self.receiver.start()

    # закрываем соединение с сервером
    def close_connection(self):
        if not self.alive:
            return

        self.alive = False

        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

        try:
            self.sock.close()
        except OSError:
            pass
    
    # отправка одной команды серверу
    def send_line(self, line):
        if not self.alive:
            print("Connection lost")
            return

        try:
            self.sock.sendall((line + "\n").encode())           # сервер читает команды построчно
        except OSError:
            self.close_connection()
            print("Connection lost")

    # читаем сокет, пока не соберём одно полное сообщение
    def read_message(self):
        while True:
            # сервер разделяет сообщения символом MSG_DELIM
            if MSG_DELIM in self.recv_buffer:
                message, self.recv_buffer = self.recv_buffer.split(MSG_DELIM, 1)
                return message

            try:
                data = self.sock.recv(4096)
            except OSError:
                return None

            if not data:
                return None

            self.recv_buffer += data.decode()

    def print_async_message(self, message):
        # readline хранит строку, которую пользователь уже начал печатать, но ещё не отправил по Enter
        current = readline.get_line_buffer()

        # очищаем текущую строку ввода
        sys.stdout.write("\r")
        sys.stdout.write(" " * (len(self.prompt) + len(current)))
        sys.stdout.write("\r")

        # печатаем асинхронное сообщение сервера
        print(message)

        # восстанавливаем prompt и уже набранный текст
        sys.stdout.write(self.prompt + current)
        sys.stdout.flush()

    # отдельный поток, который постоянно слушает сервер
    # как только от сервера приходит сообщение -> печатаем его
    def receive_loop(self):
        while self.alive:
            message = self.read_message()
            if message is None:
                break
            self.print_async_message(message)

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

        # первый аргумент - имя монстра
        # остальные параметры будем разбирать по ключам hello, hp, coords
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
                # координаты клетки, в которую ставим монстра
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
                # любой неизвестный ключ считаем ошибкой
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
    
    # поддерживаются команды:
    # attack
    # attack <monster_name>
    # attack with <weapon>
    # attack <monster_name> with <weapon>
    def do_attack(self, arg):
        try:
            line_split = shlex.split(arg)
        except ValueError:
            print("Invalid arguments")
            return

        monster_name = None
        weapon = "sword"                # оружие по умолчанию

        # attack
        if len(line_split) == 0:
            pass

        # attack <monster_name>
        elif len(line_split) == 1:
            if line_split[0] == "with":
                print("Invalid arguments")
                return
            monster_name = line_split[0]
        
        # attack with <weapon>
        elif len(line_split) == 2 and line_split[0] == "with":
            weapon = line_split[1]

        # attack <monster_name> with <weapon>
        elif len(line_split) == 3 and line_split[1] == "with":
            monster_name = line_split[0]
            weapon = line_split[2]

        
        else:
            print("Invalid arguments")
            return

        if weapon not in weapons:
            print("Unknown weapon")
            return

        # клиент отправляет серверу имя монстра и название оружия
        # сервер сам вычисляет урон и формирует ответ
        if monster_name is None:
            request = f"attack {weapon}"
        else:
            request = f"attack {shlex.quote(monster_name)} {weapon}"

        self.send_line(request)

    # автодополнение для attack
    def complete_attack(self, text, line, i_begin, i_end):          # text - имя монстра, которое уже начали вводить
        # смотрим, какая команда введена (до text)
        try:
            line_split = shlex.split(line[:i_begin])
        except ValueError:
            return []

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

    # чтобы на ctrl+D программа завершалась: Ctrl+D завершает клиент и закрывает соединение с сервером
    def do_EOF(self, arg):
        print()
        self.close_connection()
        return True


''' ----- main ----- '''

print("<<< Welcome to Python-MUD 0.1 >>>")

# имя пользователя передаётся при запуске клиента
# python3 client.py <username>
if len(sys.argv) != 2:
    print("Usage: python3 client.py <username>")
    raise SystemExit(1)

cmd_MUD(sys.argv[1]).cmdloop()
