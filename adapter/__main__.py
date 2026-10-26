import uvicorn

from adapter.config import load_settings
from adapter.main import app


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=load_settings().port)


if __name__ == "__main__":
    main()
