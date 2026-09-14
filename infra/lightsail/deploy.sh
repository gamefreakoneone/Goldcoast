set -eu
cd "$(dirname "$0")"
python3 configure.py
sudo docker compose --env-file .env config --quiet
sudo docker compose --env-file .env build api
sudo docker compose --env-file .env build gateway
sudo docker compose --env-file .env stop gateway worker api
sudo docker compose --env-file .env up -d --wait postgres
sudo docker compose --env-file .env run --rm --no-deps migrate
sudo docker compose --env-file .env up -d --no-deps --wait api worker
sudo docker compose --env-file .env up -d --no-deps gateway
sudo docker compose --env-file .env ps
