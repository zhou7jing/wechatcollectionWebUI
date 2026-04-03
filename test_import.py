#
# import pandas as pd
#
# df = pd.read_excel("data/20260316公众号监控列表.xlsx", engine="openpyxl", skiprows=2)
# print(df.columns.tolist())
#
import requests
import sqlite3
import pandas as pd

conn = sqlite3.connect("articles.db")

df = pd.read_sql("SELECT DISTINCT category FROM articles ORDER BY category", conn)
print(df,"结束")

res = requests.get(f"http://127.0.0.1:5000/api/categories", timeout=5)

print(res)



conn.close()
