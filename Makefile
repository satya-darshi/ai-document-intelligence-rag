up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api

test:
	docker compose exec api pytest -q

format:
	docker compose exec api ruff format app tests

lint:
	docker compose exec api ruff check app tests
