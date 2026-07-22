import pymysql
from config import config

conn = pymysql.connect(
    host=config.host,
    port=config.port,
    user=config.user,
    password=config.password,
    database=config.database,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)

keywords = ['nausea','vomiting','diarrhea','constipation','abdominal','rash','pruritus','headache','dizziness','somnolence','insomnia']

with conn.cursor() as c:
    for k in keywords:
        sql = "SELECT COUNT(*) as cnt FROM drug_interactions WHERE description LIKE %s"
        c.execute(sql, ('%'+k+'%',))
        row = c.fetchone()
        print(f"{k}: {row['cnt']}")

conn.close()