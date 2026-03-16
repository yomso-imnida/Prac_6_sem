from shlex import split, join

while s := input("==> "):
    print(join(split(s)))
