from __future__ import annotations
from typing import Dict, Self, Any

from .document import Document
from .operators import MongoOperators


class Query(Document):
    operator: MongoOperators
    condition: Self | Document | str | int | float | bool

    def model_dump(self) -> Dict:
        return {
            self.operator.value: (
                self.condition.model_dump()
                if isinstance(self.condition, Document)
                else self.condition
            )
        }


Query.model_rebuild()
