import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = ["planner"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]
ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": []},
}]
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --- Fuel planner settings ---
ROUTING_PROVIDER = os.environ.get("ROUTING_PROVIDER", "ors")  # "ors" or "osrm"
ORS_API_KEY = os.environ.get("ORS_API_KEY", "")
OSRM_BASE_URL = os.environ.get("OSRM_BASE_URL", "https://router.project-osrm.org")
VEHICLE_RANGE_MILES = 500
VEHICLE_MPG = 10
MAX_STATION_OFFSET_MILES = float(os.environ.get("MAX_STATION_OFFSET_MILES", "10"))
STATIONS_FILE = BASE_DIR / "data" / "stations.csv"
CITIES_FILE = BASE_DIR / "data" / "us_cities.csv"
RAW_FUEL_FILE = BASE_DIR / "data" / "raw" / "fuel-prices-for-be-assessment.csv"
