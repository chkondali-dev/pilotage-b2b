import sys

path = r'C:\Users\hachk\pilotage_b2b\app.py'
lines = open(path, encoding='utf-8').read().split('\n')
start, end = int(sys.argv[1]), int(sys.argv[2])
sys.stdout.reconfigure(encoding='utf-8')
for i in range(start - 1, min(end, len(lines))):
    print(f'{i+1:5d} | {lines[i]}')