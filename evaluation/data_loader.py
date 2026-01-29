import json

from models import EvalCase


def load_eval_dataset(file_path: str) -> list[EvalCase]:
    """
    Parses a JSON file into a list of EvalCase objects.
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            raw_data = json.load(f)

        cases = [EvalCase(**item) for item in raw_data]
        return cases
    except FileNotFoundError:
        print(f"Error: Dataset file not found at {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from {file_path}")
        return []
