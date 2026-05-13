"""Тесты для преобразования клиентских команд."""

import unittest
from unittest.mock import MagicMock, patch

from mood.client.__main__ import CmdMUD


class TestClientCommands(unittest.TestCase):
    """Тесты для преобразования пользовательских команд в команды протокола."""

    def run_client_session(self, commands):
        """Запуск клиентского цикла команд с мокерами input, socket и thread."""
        fake_socket = MagicMock()

        # имитируем первое сообщение сервера после подключения клиента
        fake_socket.recv.return_value = b"Welcome, tester\0"

        fake_thread = MagicMock()

        # если клиент проверит состояние потока -> мок ответит, что поток не работает
        fake_thread.is_alive.return_value = False

        with (
            # подменяем настоящий socket, чтобы клиент не подключался к серверу
            patch("mood.client.__main__.socket.socket", return_value=fake_socket),
            # подменяем поток получения сообщений от сервера
            patch("mood.client.__main__.threading.Thread", return_value=fake_thread),
            # подменяем пользовательский ввод: команды возвращаются по очереди
            patch("builtins.input", side_effect=[*commands, "EOF"]),
            # подменяем print, чтобы сообщения клиента не выводились в тестах
            patch("builtins.print") as mock_print,
        ):
            client = CmdMUD("tester")
            client.intro = ""
            client.prompt = ""
            client.cmdloop()        # запускаем цикл клиента (как при ручном вводе команд)

        return fake_socket, mock_print

    def assert_command_was_sent(self, fake_socket, command):
        """Проверка, что команда протокола была отправлена на сервер."""
        fake_socket.sendall.assert_any_call((command + "\n").encode())

    def test_right_command(self):
        """Движение вправо преобразуется в move 1 0."""
        fake_socket, _ = self.run_client_session(["right"])     # запускаем клиент с одной пользовательской командой

        self.assert_command_was_sent(fake_socket, "move 1 0")   # проверяем, что клиент отправил серверу команду

    def test_left_command(self):
        """Движение влево преобразуется в move -1 0."""
        fake_socket, _ = self.run_client_session(["left"])

        self.assert_command_was_sent(fake_socket, "move -1 0")

    def test_attack_with_weapon(self):
        """Attack with <weapon> преобразуется в attack <weapon>."""
        fake_socket, _ = self.run_client_session(["attack with spear"])

        self.assert_command_was_sent(fake_socket, "attack spear")

    def test_attack_monster_with_weapon(self):
        """Attack <monster> with <weapon> преобразуется в attack <monster> <weapon>."""
        fake_socket, _ = self.run_client_session(["attack dragon with axe"])

        self.assert_command_was_sent(fake_socket, "attack dragon axe")

    def test_wrong_attack_weapon(self):
        """Неправильное оружие отклоняется (и не отправляется на сервер)."""
        fake_socket, mock_print = self.run_client_session(["attack dragon with spoon"])

        fake_socket.sendall.assert_called_once_with(b"tester\n")
        mock_print.assert_any_call("Unknown weapon")


if __name__ == "__main__":
    unittest.main()
