#!/usr/bin/env python3
import os
from pydantic import Field
import pytest

from dotenv import load_dotenv

from db import (
    DBClient,
    Document,
    WriteDocument,
    ReadDocument,
    MongoOperators,
    Query,
)

load_dotenv()

HOST = os.environ.get("MONGO_HOST", "localhost")
PORT = int(os.environ.get("MONGO_PORT", 27017))
COLLECTION = os.environ.get("MONGO_COLLECTION", "test")


class UserBase(Document):
    name: str
    email: str
    age: int = Field(int, gt=0)


class UserWrite(UserBase, WriteDocument):
    pass


class UserRead(UserBase, ReadDocument):
    pass


@pytest.fixture
def mongodb():
    db = DBClient(HOST, PORT, COLLECTION)
    assert db.client.admin.command("ping")["ok"] != 0.0
    return db


@pytest.fixture
def collection():
    return "users"


@pytest.fixture
def data():
    return UserWrite(name="John Doe", email="john.doe@mail.com", age=30)


@pytest.fixture
def query():
    operator = MongoOperators.SET
    condition = Document(age=31)  # Should be { "age": 31 }
    return Query(operator=operator, condition=condition)
