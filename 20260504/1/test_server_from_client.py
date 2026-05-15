"""Тестирование отработки сервером команд от клиента."""

import multiprocessing
import socket
import time
import unittest

from mood.common.constants import HOST, MSG_DELIM, PORT
from mood.server.__main__ import serve


class TestServerFromClient(unittest.TestCase):
    """Тесты для команд сервера."""

    def setUp(self):
        """Запуск сервера и подключение к нему одного клиента."""
        self.proc = multiprocessing.Process(target=serve)
        self.proc.start()
        time.sleep(1)               # даём серверу время запуститься и начать слушать порт

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))

        # первой строкой клиент отправляет имя пользователя
        self.username = "tester"
        self.send_raw(self.username)

        # сервер должен подтвердить успешное подключение
        reply = self.read_block()
        self.assertEqual(reply, f"Welcome, {self.username}")

        # отключаем движение монстров, чтобы тесты были детерминированными
        self.send_raw("movemonsters off")
        reply = self.read_block()
        self.assertEqual(reply, "Moving monsters: off")

        # включаем русскую локаль для проверки русскоязычных ответов сервера
        self.send_raw("locale ru_RU.UTF-8")
        reply = self.read_block()
        self.assertEqual(reply, "Установлена локаль: ru_RU.UTF-8")

    def tearDown(self):
        """Закрытие клиентского сокета и остановка сервера."""
        self.sock.close()
        self.proc.terminate()
        self.proc.join()

    def send_raw(self, message):
        """Отправка одной строки на сервер."""
        self.sock.sendall((message + "\n").encode())

    def read_block(self):
        """Чтение одного сообщения с сервера (полностью)."""
        data = ""

        # сервер разделяет сообщения спецсимволом MSG_DELIM, поэтому читаем данные
        # до тех пор, пока не получим одно полное сообщение
        while MSG_DELIM not in data:
            chunk = self.sock.recv(4096)

            if not chunk:
                break

            data += chunk.decode()

        # берём только первое сообщение до разделителя
        message, _, _ = data.partition(MSG_DELIM)
        return message

    def test_addmon(self):
        """Проверка обработки сервером команды добавления монстра рядом с игроком."""
        # отправляем команду протокола для создания монстра рядом с начальной позицией
        self.send_raw("addmon dragon hello 30 1 0")
        reply = self.read_block()

        # сервер должен подтвердить имя, координаты и hp добавленного монстра
        self.assertEqual(
            reply,
            "tester добавил монстра dragon в (1, 0), здоровье: 30 очков здоровья",
        )

    def test_move_to_monster(self):
        """Сервер отправляет клиенту приветствие монстра после прихода к нему."""
        # создаем монстра в соседней клетке справа от игрока
        self.send_raw("addmon dragon hello 30 1 0")
        reply = self.read_block()
        self.assertEqual(
            reply,
            "tester добавил монстра dragon в (1, 0), здоровье: 30 очков здоровья",
        )

        # передвигаем игрока на клетку с монстром
        self.send_raw("move 1 0")

        # первым сообщением сервер подтверждает новое положение игрока
        move_reply = self.read_block()
        self.assertEqual(move_reply, "Moved to (1, 0)")

        # сервер отправляет сообщение встречи с монстром и его приветствием
        monster_reply = self.read_block()
        self.assertIn("hello", monster_reply)

    def test_attack_monster(self):
        """Проверка обработки сервером команды атаки."""
        # создаем монстра рядом с игроком, чтобы до него можно было дойти одним шагом
        self.send_raw("addmon dragon hello 30 1 0")
        reply = self.read_block()
        self.assertEqual(
            reply,
            "tester добавил монстра dragon в (1, 0), здоровье: 30 очков здоровья",
        )

        # переходим на клетку с монстром
        self.send_raw("move 1 0")
        move_reply = self.read_block()
        self.assertEqual(move_reply, "Moved to (1, 0)")

        # после перемещения сервер дополнительно присылает приветствие монстра
        self.read_block()

        # атакуем конкретного монстра конкретным оружием
        self.send_raw("attack dragon sword")
        reply = self.read_block()

        self.assertEqual(
            reply,
            "tester атаковал dragon с помощью sword, урон 10 очков здоровья, "
            "у dragon осталось 20 очков здоровья",
        )


if __name__ == "__main__":
    unittest.main()
