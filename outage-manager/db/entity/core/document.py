#!/usr/bin/env python3
from typing import Annotated
from bson import ObjectId
from pydantic import (
    BaseModel,
    Field,
    AfterValidator,
    PlainSerializer,
    WithJsonSchema,
    ConfigDict,
)


class Document(BaseModel):
    model_config: ConfigDict = ConfigDict(extra="allow")


def validate_object_id(value: str | ObjectId) -> ObjectId:
    if isinstance(value, ObjectId):
        return value
    if not ObjectId.is_valid(value):
        raise ValueError("Invalid ObjectId")
    return ObjectId(value)


MongoObjectId = Annotated[
    str,
    Field(..., alias="_id", description="MongoDB ObjectId"),
    AfterValidator(validate_object_id),
    PlainSerializer(lambda v: str(v), return_type=str),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]


class ReadDocument(Document):
    object_id: MongoObjectId = Field(..., alias="_id")


class WriteDocument(Document):
    pass
