CATCHUP_EACH = 20
CATCHUP_BATCH_MAX = 200
CATCHUP_BATCH_SIZE = 20
CATCHUP_TAIL = 20


def catchup_mode(count: int) -> str:
    if count <= CATCHUP_EACH:
        return "each"
    if count <= CATCHUP_BATCH_MAX:
        return "batch"
    return "summary"


def chunk_items(items: list, size: int = CATCHUP_BATCH_SIZE) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]
