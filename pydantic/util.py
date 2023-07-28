from contextlib import contextmanager
from pydantic import (
    ValidationError,
)
from typing import Iterator

def is_recursion_validation_error(exc: ValidationError) -> bool:
    errors = exc.errors()
    return len(errors) == 1 and errors[0]["type"] == "recursion_loop"


@contextmanager
def suppress_recursion_validation_error() -> Iterator[None]:
    try:
        yield
    except ValidationError as exc:
        if not is_recursion_validation_error(exc):
            raise exc
