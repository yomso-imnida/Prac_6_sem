import sys, os

# печать списка веток
def heads_list():
    # ветки лежат в .git/refs/heads/
    path_heads = sys.argv[1] + ".git/refs/heads/"
    
    for name in os.listdir(path_heads):
        print(name)

# нахождение последнего коммита
# id коммита лежит в .git/refs/heads/branch
def commit_branch(branch):
    path_branch = sys.argv[1] + ".git/refs/heads/branch" + branch

    file = open(path_branch)
    sha = file.read().strip()

    file.close()

    return sha

# ввели только путь к каталогу
if len(sys.argv) == 2:
    heads_list()

# ввели путь к каталогу и имя ветки
elif len(sys.argv) == 3:
    print(commit_branch(sys.argv[2]))
