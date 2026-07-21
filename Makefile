.PHONY: demo demo-down reset test

demo:
	docker compose up --build

demo-down:
	docker compose down

reset:
	docker compose exec api python -m app.reset

test:
	docker compose run --rm -v "$(CURDIR)/backend/tests:/app/tests:ro" api pytest -q
