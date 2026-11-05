from pathlib import Path
from dotenv import dotenv_values

envPath = Path(__file__).parent / ".env"
print("Path:", envPath)
print("Exists:", envPath.exists())
print("Size in bytes:", envPath.stat().st_size if envPath.exists() else "n/a")
print("Keys found:", list(dotenv_values(envPath).keys()))