import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()  # reads your .env file

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
print("Connected successfully!")
conn.close()