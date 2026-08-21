.PHONY: test lint typecheck seed-demo seed-reset seed-case seed-registry

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy

seed-demo:
	docker compose -f infra/docker/docker-compose.yml up -d
	docker compose -f infra/docker/docker-compose.yml exec api python scripts/seed_demo.py

seed-reset: seed-demo

seed-case:
	docker compose -f infra/docker/docker-compose.yml up -d
	docker compose -f infra/docker/docker-compose.yml exec api python scripts/seed_demo.py --case $(CASE)

seed-registry:
	docker compose -f infra/docker/docker-compose.yml up -d
	docker compose -f infra/docker/docker-compose.yml exec api python scripts/seed_registry.py
