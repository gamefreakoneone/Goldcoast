set -eu
cd "$(dirname "$0")"
umask 077
backup_dir="$(pwd)/../../output/hosted-backups/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"
compose() { sudo docker compose --env-file .env "$@"; }
trap 'compose start api worker gateway' EXIT
compose stop gateway worker api
compose exec -T postgres pg_dump -U goldcoast -d goldcoast --clean --if-exists > "$backup_dir/database.sql"
compose run --rm --no-deps --entrypoint tar migrate -C /app/output/studio -czf - . > "$backup_dir/studio.tar.gz"
cp .env "$backup_dir/config.env"
printf 'Backup saved to %s. Copy it off the server and keep it private.\n' "$backup_dir"
