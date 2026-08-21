IBU_ID ?= IBU-A

.PHONY: test lint typecheck deploy-staging rollback-staging health-check seed-demo seed-demo-local seed-reset seed-case seed-registry demo-token

test:
	pytest

lint:
	ruff check .

typecheck:
	mypy

seed-demo:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/seed_staging.ps1

seed-demo-local:
	docker compose -f infra/docker/docker-compose.yml up -d
	docker compose -f infra/docker/docker-compose.yml exec api python scripts/seed_demo.py

seed-reset: seed-demo-local

seed-case:
	docker compose -f infra/docker/docker-compose.yml up -d
	docker compose -f infra/docker/docker-compose.yml exec api python scripts/seed_demo.py --case $(CASE)

seed-registry:
	docker compose -f infra/docker/docker-compose.yml up -d
	docker compose -f infra/docker/docker-compose.yml exec api python scripts/seed_registry.py

deploy-staging:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/deploy_staging.ps1

rollback-staging:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/rollback_staging.ps1

health-check:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/health_check_staging.ps1

demo-token:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/issue_demo_token.ps1 -IbuId $(IBU_ID)
