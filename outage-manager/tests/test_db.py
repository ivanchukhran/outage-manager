#!/usr/bin/env python3

from db import DBClient, Document, Query, MongoOperators


def test_db_fixture(mongodb):
    assert mongodb.client.admin.command("ping")["ok"] > 0


def test_user_fixture(data):
    assert data.name == "John Doe"
    assert data.email == "john.doe@mail.com"
    assert data.age == 30


def test_query_fixture(query: Query):
    query_dump = query.model_dump()
    assert query_dump == {"$set": {"age": 31}}


def test_insert(mongodb, data, collection):
    result = mongodb.insert(collection, data)
    assert result.acknowledged
    assert result.inserted_id is not None


def test_find_one(mongodb, data, collection):
    mongodb.insert(collection, data)
    result = mongodb.find_one(collection, data)
    assert result is not None
    assert result["name"] == data.name
    assert result["email"] == data.email
    assert result["age"] == data.age


def test_update(mongodb: DBClient, data, collection, query):
    mongodb.insert(collection, data)
    result = mongodb.update_one(collection, data, query)
    assert result.acknowledged
    assert result.modified_count == 1
    # assert result.n == 1


def test_delete(mongodb, collection, data):
    mongodb.insert(collection, data)
    result = mongodb.delete(collection, data)
    assert result.acknowledged
    assert result.deleted_count == 1
