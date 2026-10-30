.PHONY: install dev backend build test launch
install:
	./scripts/install.sh
backend:
	.venv/bin/python -m chopin
dev:
	@.venv/bin/python -m chopin & backend_pid=$$!; trap 'kill $$backend_pid 2>/dev/null || true' EXIT INT TERM; cd frontend && pnpm dev
build:
	cd frontend && pnpm build
test:
	.venv/bin/python -m pytest -q
	cd frontend && pnpm test
launch:
	.venv/bin/python scripts/launch.py
