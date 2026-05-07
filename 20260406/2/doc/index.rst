.. MOOD documentation master file, created by
   sphinx-quickstart on Wed May  6 15:06:55 2026.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

MOOD documentation
==================

MOOD - многопользовательская игра, где игроки перемещаются
по закольцованному полю, добавляют монстров, атакуют их и обмениваются
сообщениями.

Запуск (обычный режим)
----------------------

Сервер запускается командой::

   python3 -m mood.server

Клиент запускается командой::

   python3 -m mood.client <user_name>

Например::

   python3 -m mood.client alice

Имя пользователя передаётся серверу при подключении. Если такое имя уже
занято, сервер отклоняет подключение.

Режим с файлом
--------------

Клиент может читать команды из файла::

   python3 -m mood.client <user_name> --file <commands_file>

Например::

   python3 -m mood.client alice --file test.mood

В этом режиме команды берутся из файла, обычный ввод через ``cmd`` не
используется. Между отправками команд на сервер выдерживается пауза
не менее 1 секунды.

Пример файла ``test.mood``::

   sayall "Hello from file"
   addmon dragon hello "Hi, I'm dragon :)" hp 30 coords 1 0
   right
   attack dragon with sword
   attack dragon with axe
   EOF

Игровое поле
------------

Поле размером 10x10. Координаты закольцованы: если игрок выходит
за границу поля, он появляется с противоположной стороны.

Например, переход вверх из клетки ``(0, 0)`` приводит в клетку ``(0, 9)``.

Команды для пользователя
------------------------

Движение игрока::

   up
   down
   left
   right

Добавление монстра::

   addmon <monster_name> hello <message> hp <hp> coords <x> <y>

Например::

   addmon dragon hello "I am dragon" hp 30 coords 1 0

Атака монстра::

   attack
   attack <monster_name>
   attack with <weapon>
   attack <monster_name> with <weapon>

Доступное оружие::

   sword
   spear
   axe

Отправка сообщения всем игрокам::

   sayall <message>

Например::

   sayall "Let's attack dragon"

Монстры
-------

Монстр хранит имя, приветственную фразу и количество здоровья.

Если игрок попадает на клетку с монстром, сервер отправляет ему сообщение
с изображением монстра и его приветственной фразой.

Один раз в 30 секунд сервер перемещает случайного монстра на одну клетку
в случайном направлении. Если новая клетка занята другим монстром,
выбирается другой ход.

При успешном перемещении монстра все игроки получают сообщение вида::

   dragon moved one cell right

Техническая документация
------------------------

Ссылка на техническую документацию находится ниже:

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   API