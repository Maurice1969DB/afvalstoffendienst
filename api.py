import os
from typing import Optional

from fastapi import FastAPI
from flask.cli import load_dotenv
from sqlmodel import Field, Session, SQLModel, create_engine, select

from src import scrape


class Date(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str
    date: str


SQLITE_FILE_NAME = "database.db"
sqlite_url = f"sqlite:///{SQLITE_FILE_NAME}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=True, connect_args=connect_args)

app = FastAPI()


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def delete_all():
    with Session(engine) as session:
        session.query(Date).delete()
        session.commit()


def fill_table():
    postal_code = os.getenv("POSTAL_CODE")
    number = os.getenv("NUMBER")
    scraper = scrape.Scrape(postal_code, number)
    with Session(engine) as session:
        for k, dates in scraper.reminder_dates_for_all_kinds.items():
            for date in dates:
                session.add(Date(kind=k, date=date))
        session.commit()
    return True


@app.on_event("startup")
def on_startup():
    load_dotenv()
    create_db_and_tables()
    delete_all()
    fill_table()


@app.get("/dates")
def all_dates():
    with Session(engine) as session:
        dates = session.exec(select(Date)).all()
        return dates


@app.get("/dates/{date}")
def reminder_date(date: str):
    with Session(engine) as session:
        return session.exec(select(Date).where(Date.date == date)).first()