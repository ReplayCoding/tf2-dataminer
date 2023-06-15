import sqlite3
import sys
import csv

w = csv.writer(sys.stdout, delimiter=",")

con = sqlite3.connect(sys.argv[1])
cur = con.cursor()
res = cur.execute("SELECT address1, address2, name1, name2, similarity, confidence FROM function ORDER BY similarity")

w.writerow(["similarity", "address1", "name1", "address2", "name2", "confidence"])
for row in res.fetchall():
	address1, address2, name1, name2, similarity, confidence = row
	w.writerow([round(similarity * 100, 2), hex(address1), name1, hex(address2), name2, round(confidence * 100, 2)])
