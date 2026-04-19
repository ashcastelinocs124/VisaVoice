import uvicorn

from pathlib import Path
from .app import create_app


def main() -> None:
    app = create_app(data_dir=Path("backend_data"))
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    main()
