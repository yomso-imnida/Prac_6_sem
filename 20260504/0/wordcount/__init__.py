
from pathlib import Path

PATH = Path(__file__).absolute().parent

def main():
	import gettext
	import locale
	locale = locale.setlocale(locale.LC_ALL, locale.getlocale())
	translation = gettext.translation("wordcount", PATH, fallback=True)
	ngettext = translation.ngettext

	words = input().split()
	n = len(words)
	print(ngettext("Entered {} word", "Entered {} words", n).format(n))
