import locale
import gettext

locale = locale.setlocale(locale.LC_ALL, locale.getlocale())
translation = gettext.translation("wordcount", "po", fallback=True)
tolmatch = gettext.translation("wordecounte", "po", fallback=True)
ngettext, ngette = translation.ngettext, tolmatch.ngettext

words = input().split()
n = len(words)
print(ngettext("Entered {} word", "Entered {} words", n).format(n))
print(ngette("Entered {} word", "Entered {} words", n).format(n))
