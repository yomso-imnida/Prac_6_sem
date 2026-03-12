import sys, os

# печать списка веток
def heads_list():
    # ветки лежат в .git/refs/heads/
    path_heads = sys.argv[1] + ".git/refs/heads/"
    for name in os.listdir(path_heads):
        print(name)


# ввели только путь к каталогу
if len(sys.argv) == 2:
    heads_list()

# ввели путь к каталогу и имя ветки
elif len(sys.argv) == 3:
    
