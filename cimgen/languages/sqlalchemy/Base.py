from sqlalchemy.orm import DeclarativeBase


class BaseClass(DeclarativeBase):
    def to_dict(self) -> dict:
        python_dict = {}
        for key, value in self.__dict__.items():
            if not key.startswith("_") and key != "objectType":
                if isinstance(value, list):
                    transformed_list = []
                    for element in value:
                        if isinstance(element, DeclarativeBase):
                            transformed_list.append(element.to_dict())
                        else:
                            transformed_list.append(element)
                    value = transformed_list
                if isinstance(value, DeclarativeBase):
                    value = value.to_dict()
                python_dict[key] = value
        return python_dict

    pass
