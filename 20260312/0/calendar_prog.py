import cmd
from shlex import split
from pathlib import Path
from calendar import TextCalendar

class SizeCmdl(cmd.Cmd):
    prompt = "==> "

    def do_size(self, arg):
        """Print file sizes"""
        args = split(arg)
        for name in args:
            print(f"{name}: {Path(name).stat().st_size}")

    def do_month(self, arg):
        """Print a month’s calendar"""
        args = split(arg)
        if len(args) == 2:
            TextCalendar().prmonth(int(args[0]),int(args[1]))
        else:
            print("no args")

    def do_year(self, arg):
        """Print the calendar for an entire year"""
        TextCalendar().pryear(int(arg))
              

    def do_EOF(self, arg):
        print("\nBye\n")
        return 1


if __name__ == "__main__":
    SizeCmdl().cmdloop()
