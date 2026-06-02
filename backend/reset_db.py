import sys
import os

# Add the current directory to python path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.database.db import engine, Base
from sqlalchemy.orm import Session
from app.api.endpoints import seed_default_policies

print("Dropping all tables...")
try:
    Base.metadata.drop_all(bind=engine)
    print("Tables dropped.")
except Exception as e:
    print(f"Error dropping tables: {e}")

print("Creating all tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("Tables created.")
except Exception as e:
    print(f"Error creating tables: {e}")

print("Seeding default policies and historical data...")
try:
    db = Session(bind=engine)
    seed_default_policies(db)
    db.close()
    print("Database reset and seeded successfully!")
except Exception as e:
    print(f"Error seeding database: {e}")
