while s := input("==> "):
    cmd, *args = s.split()
    print(cmd, len(args), args)
