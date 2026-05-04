import sys
import calendar

cal = calendar.month(int(sys.argv[1]), int(sys.argv[2])).split('\n')
cal[0] = ".. table:: " + cal[0].strip()
cal[-1] = '== == == == == == =='
cal.insert(2, '== == == == == == ==')
cal.insert(1, '== == == == == == ==')
cal.insert(1, '')

for i in range(1, len(cal)):
    cal[i] = '    ' + cal[i]

print('\n'.join(cal))