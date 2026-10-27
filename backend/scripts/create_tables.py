from app.database import Base, engine
from app.models import ResearchJob


def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
    print("Created table:", ResearchJob.__tablename__)


if __name__ == "__main__":
    create_tables()