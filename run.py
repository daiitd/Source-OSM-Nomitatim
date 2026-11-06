import sys
from app import create_app
from app.config import Config

def main():
    app = create_app()
    port = Config.PORT
    host = Config.HOST

    print("=" * 70)
    print(" MID SOFTWARE - OPENSTREETMAP × NOMINATIM BACKEND POC (TUẦN 3)")
    print("=" * 70)
    print(f" * Server running on: http://localhost:{port}")
    print(f" * Interactive Demo Dashboard: http://localhost:{port}/")
    print(f" * OpenAPI / Swagger Docs:     http://localhost:{port}/docs")
    print(f" * Search Endpoint:            http://localhost:{port}/api/v1/geocode/search")
    print(f" * Reverse Endpoint:           http://localhost:{port}/api/v1/geocode/reverse")
    print(f" * Upstream Target:            {Config.NOMINATIM_BASE_URL}")
    print(f" * User-Agent:                 {Config.USER_AGENT}")
    print("=" * 70)
    print(" Press Ctrl+C to stop the server.\n")

    app.run(host=host, port=port, debug=Config.DEBUG)

if __name__ == "__main__":
    main()

