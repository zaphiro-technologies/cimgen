from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    def to_dict(self) -> dict:
        python_dict = {}
        for key, value in vars(self).items():
            if not key.startswith("_") and key != "objectType":
                python_dict[key] = value
        return python_dict

    pass
