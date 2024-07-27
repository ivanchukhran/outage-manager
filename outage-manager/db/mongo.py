#!/usr/bin/env python3
from pymongo import MongoClient
from .entity import Document, Query


class DBClient:
    def __init__(self, host, port, db_name):
        self.client = MongoClient(host, port)
        self.db = self.client[db_name]

    def insert(self, collection, data: Document):
        return self.db[collection].insert_one(data.model_dump())

    def insert_many(self, collection: str, data: list[Document]):
        return self.db[collection].insert_many([d.model_dump() for d in data])

    def find(self, collection: str, query: Query):
        return self.db[collection].find(query.model_dump())

    def find_one(self, collection: str, query: Query):
        return self.db[collection].find_one(query.model_dump())

    def update_one(self, collection: str, data: Document, query: Query):
        return self.db[collection].update_one(
            data.model_dump(), query.model_dump()
        )

    def delete(self, collection: str, query: Query):
        return self.db[collection].delete_one(query.model_dump())

    def delete_many(self, collection: str, query: Query):
        return self.db[collection].delete_many(query.model_dump())
