from . import __version__
import os 
import uvicorn
from dotenv import load_dotenv
load_dotenv()
from .api.routes import app



def main() -> None:
    """
    the entry point of the backend
    """

    print(f"Backend version: {__version__}")
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host=host, port=port)





if __name__ == "__main__":
    main()