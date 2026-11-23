.PHONY: setup up down logs test test-backend test-browser test-proxy frontend-build clean

setup:
	python scripts/bootstrap_local.py

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

test: test-backend test-browser test-proxy

test-backend:
	cd backend && python -m pytest -q

test-browser:
	cd browser_agent && python -m pytest -q

test-proxy:
	cd egress_proxy && python -m pytest -q

frontend-build:
	cd frontend && npm install && npm run build

clean:
	docker compose down -v
