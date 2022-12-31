.PHONY: fmt

fmt:
	black orgy.py
	isort orgy.py

.venv:
	./util/venv.sh
