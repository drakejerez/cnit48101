# Compose targets
up:
    docker compose up -d

down:
    docker compose down

dev:
    docker compose --profile dev up

prod:
    docker compose up --build

obs:
    docker compose --profile obs up

logs:
    docker compose logs -f

clean:
    docker system prune -af

override:
    docker compose -f docker-compose.yml -f docker-compose.override.yml up
