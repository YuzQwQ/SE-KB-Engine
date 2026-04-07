import json
from pathlib import Path


def make_validator():
    def _validate(obj: dict, schema_path: str):
        try:
            import jsonschema

            sp = Path(schema_path)
            schema = json.loads(sp.read_text(encoding="utf-8"))
            jsonschema.validate(instance=obj, schema=schema)
            return True, []
        except Exception as e:
            return False, [str(e)]

    return _validate
