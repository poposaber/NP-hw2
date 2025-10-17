import json

class Message:
    def __init__(self, data_dict: dict = {}) -> None:
        self.data = data_dict

    def to_json(self) -> str:
        return json.dumps(self.data)
    
    @classmethod
    def from_json(cls, json_str: str):
        data_dict = json.loads(json_str)
        return cls(data_dict)

        