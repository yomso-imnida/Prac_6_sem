from shlex import split

while s := input("==> "):
    cmd, *args = split(s)
    print(cmd, len(args), args)
