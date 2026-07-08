.PHONY: help install test lint clean phase0-5 phase1 azure-setup

help:
	@echo "J-space Observation Project"
	@echo "============================"
	@echo "Available targets:"
	@echo "  make install        - Install project in editable mode"
	@echo "  make test           - Run unit tests"
	@echo "  make lint           - Run linting checks"
	@echo "  make clean          - Remove build artifacts"
	@echo "  make phase0-5       - Run Phase 0.5 spike (local)"
	@echo "  make phase1         - Run Phase 1 (local)"
	@echo "  make phase1-dry     - Run Phase 1 in dry-run mode"
	@echo "  make azure-setup    - Setup Azure infrastructure"
	@echo "  make azure-phase0-5 - Submit Phase 0.5 to Azure"
	@echo "  make azure-phase1   - Submit Phase 1 to Azure"

install:
	pip install -e .
	pip install -r requirements.txt

test:
	pytest tests/ -v

lint:
	python -m pylint src/jspace_observation/ --exit-zero

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/

phase0-5:
	python experiments/phase0_5_jlens_spike.py --skip-fit

phase1:
	python experiments/phase1_depth_gradient.py

phase1-dry:
	python experiments/phase1_depth_gradient.py --dry-run

azure-setup:
	bash infra/azure/scripts/00_check_prereqs.sh
	bash infra/azure/scripts/01_build_and_push_image.sh

azure-phase0-5:
	bash infra/azure/scripts/02_run_phase0_5.sh

azure-phase1:
	bash infra/azure/scripts/03_run_phase1.sh

.PHONY: help install test lint clean phase0-5 phase1 phase1-dry azure-setup azure-phase0-5 azure-phase1
