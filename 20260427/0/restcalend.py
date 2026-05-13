import sys
import calendar

def main():
    """Основная функция, которая генерирует таблицу календаря."""
    if len(sys.argv) < 3:
        print("Usage: python restcalend.py <year> <month>")
        sys.exit(1)
    
    try:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
    except ValueError:
        print("Error: Year and month must be numbers")
        sys.exit(1)
    
    cal = calendar.month(year, month).split('\n')
    cal[0] = ".. table:: " + cal[0].strip()
    cal[-1] = '== == == == == == =='
    cal.insert(2, '== == == == == == ==')
    cal.insert(1, '== == == == == == ==')
    cal.insert(1, '')
    
    for i in range(1, len(cal)):
        cal[i] = '    ' + cal[i]
    
    print('\n'.join(cal))

if __name__ == "__main__":
    main()