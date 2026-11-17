import sqlite3, sys
c = sqlite3.connect('/app/sia/data/sia.db')
for q in sys.argv[1:]:
    for r in c.execute(q):
        print(r)
    print('---')
