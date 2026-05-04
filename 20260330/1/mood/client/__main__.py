""" Запуск клиентского MUD-а """

import cmd
import shlex
import socket
import sys
import threading
import readline

from mood.common.constants import HOST, MSG_DELIM, PORT, WEAPONS
from mood.server.game import get_monsters


class CmdMUD(cmd.Cmd):
    """ CMD (командная строка) для клиента """

    prompt = ">>> "

    '''
        Клиент:
        - читает команды, отправляет их серверу
        - отдельно получает асинхронные сообщения
    '''

    def __init__(self, username):
        """ подключение клиента к серверу, запуск потока для связи с сервером """

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

    def close_connection(self):
        """ завершение соединения с сервером """

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

    def send_line(self, line):
        """ отправка одной команды на сервер """

        if not self.alive:
            print("Connection lost")
            return

        try:
            self.sock.sendall((line + "\n").encode())           # сервер читает команды построчно
        except OSError:
            self.close_connection()
            print("Connection lost")

    def read_message(self):
        """ чтение сокета, пока не соберётся одно полное сообщение """

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
        """ вывод сообщения сервера (без потери текущего ввода) """

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

    def receive_loop(self):
        """ получение сообщения от сервера в фоновом режиме """

        # отдельный поток, который постоянно слушает сервер
        # как только от сервера приходит сообщение -> печатаем его

        while self.alive:
            message = self.read_message()
            if message is None:
                break
            self.print_async_message(message)

        self.alive = False

    # если есть аргументы у движения - ошибка

    def do_up(self, arg):
        """ перемещение игрока вверх (up -> (0, -1)) """

        if arg:
            print("Invalid arguments")
            return
        self.send_line("move 0 -1")

    def do_down(self, arg):
        """ перемещение игрока вниз (down -> (0, 1)) """

        if arg:
            print("Invalid arguments")
            return
        self.send_line("move 0 1")

    def do_left(self, arg):
        """ перемещение игрока влево (left -> (-1, 0)) """

        if arg:
            print("Invalid arguments")
            return
        self.send_line("move -1 0")

    def do_right(self, arg):
        """ перемещение игрока вправо (right -> (1, 0)) """

        if arg:
            print("Invalid arguments")
            return
        self.send_line("move 1 0")

    def do_addmon(self, arg):
        """ добавление монстра в клетку на игровом поле """

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
                    if (i + 1) >= len(line_split):
                        print("Invalid arguments")
                        flag = True
                        break
                    hello = line_split[i + 1]
                    i += 2

                # ----- hp -----
                case "hp":
                    if (i + 1) >= len(line_split):
                        print("Invalid arguments")
                        flag = True
                        break

                    try:
                        hp = int(line_split[i + 1])
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
                    if (i + 2) >= len(line_split):
                        print("Invalid arguments")
                        flag = True
                        break

                    try:
                        x = int(line_split[i + 1])
                        y = int(line_split[i + 2])
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

    def do_attack(self, arg):
        """ атака монстра в текущей клетке """

        '''
        поддерживаются команды:
            attack
            attack <monster_name>
            attack with <weapon>
            attack <monster_name> with <weapon>
        '''

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

        if weapon not in WEAPONS:
            print("Unknown weapon")
            return

        # клиент отправляет серверу имя монстра и название оружия
        # сервер сам вычисляет урон и формирует ответ
        if monster_name is None:
            request = f"attack {weapon}"
        else:
            request = f"attack {shlex.quote(monster_name)} {weapon}"

        self.send_line(request)

    def do_sayall(self, arg):
        """ отправка сообщения всем игрокам (сообщение должно быть одним словом или одной строкой в кавычках) """

        try:
            # sayall <слово>
            # sayall "<выражение  пробелами>"
            line_split = shlex.split(arg)
        except ValueError:
            print("Invalid arguments")
            return

        if len(line_split) != 1:
            print("Invalid arguments")
            return

        message = line_split[0]
        self.send_line(f"sayall {shlex.quote(message)}")

    def complete_attack(self, text, line, i_begin, i_end):
        """ автодополнение для команды атаки """

        # text - имя монстра, которое уже начали вводить
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
            return [name for name in WEAPONS if name.startswith(text)]

        if (len(line_split) == 3) and (line_split[0] == "attack") and (line_split[2] == "with"):
            # смотрим на оружие   (после attack <monster> with)
            return [name for name in WEAPONS if name.startswith(text)]

        return []

    def default(self, arg):
        """ обработка неизвестных команд """

        print("Invalid command")

    def emptyline(self):
        """ игнорирование пустой строки (в вводе) """
        pass

    def do_EOF(self, arg):
        """ чтобы на ctrl+D программа завершалась: Ctrl+D завершает клиент и закрывает соединение с сервером """

        print()
        self.close_connection()
        return True


def main():
    """ запуск MUD-клиент """

    print("<<< Welcome to Python-MUD 0.1 >>>")

    # имя пользователя передаётся при запуске клиента
    # python3 -m mood.client <username>
    if len(sys.argv) != 2:
        print("Usage: python3 -m mood.client <username>")
        raise SystemExit(1)

    CmdMUD(sys.argv[1]).cmdloop()

if __name__ == "__main__":
    main()
