import os
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
print("URL found:", url is not None)

from sqlalchemy import create_engine, text

engine = create_engine(url)
with engine.connect() as conn:
    print("Connected! Result:", conn.execute(text("select 1")).scalar())