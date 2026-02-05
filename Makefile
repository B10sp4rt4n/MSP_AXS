# Makefile para MSP_AXS - Comandos de desarrollo

.PHONY: help install test coverage lint format clean run dev

help:  ## Mostrar este mensaje de ayuda
	@echo "Comandos disponibles:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Instalar dependencias
	pip install -r requirements.txt
	pre-commit install

test:  ## Ejecutar tests
	pytest tests/ -v

test-fast:  ## Ejecutar tests rápidos (sin cobertura)
	pytest tests/ -v -x --tb=short

coverage:  ## Ejecutar tests con reporte de cobertura
	pytest tests/ --cov=backend --cov-report=term --cov-report=html
	@echo "\n✅ Reporte HTML generado en htmlcov/index.html"

coverage-core:  ## Cobertura solo de módulos core
	pytest tests/ --cov=backend/core --cov-report=term

lint:  ## Ejecutar linters (flake8)
	flake8 backend/ --max-line-length=100 --extend-ignore=E203,W503

format:  ## Formatear código con Black
	black backend/ tests/ --line-length=100
	isort backend/ tests/ --profile=black --line-length=100

format-check:  ## Verificar formato sin modificar
	black backend/ tests/ --check --line-length=100
	isort backend/ tests/ --check --profile=black --line-length=100

type-check:  ## Verificar tipos con MyPy
	mypy backend/ --ignore-missing-imports --no-strict-optional

pre-commit:  ## Ejecutar pre-commit hooks manualmente
	pre-commit run --all-files

clean:  ## Limpiar archivos generados
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Limpieza completada"

run:  ## Iniciar servidor en producción
	uvicorn backend.main:app --host 0.0.0.0 --port 8000

dev:  ## Iniciar servidor en modo desarrollo (hot reload)
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

check-all:  ## Ejecutar todas las verificaciones (format, lint, type, test)
	@echo "🔍 Verificando formato..."
	@make format-check
	@echo "\n🔍 Ejecutando linters..."
	@make lint
	@echo "\n🔍 Verificando tipos..."
	@make type-check
	@echo "\n🧪 Ejecutando tests..."
	@make test
	@echo "\n✅ Todas las verificaciones pasaron!"

ci:  ## Simular CI pipeline localmente
	@echo "🚀 Simulando pipeline CI..."
	@make clean
	@make format-check
	@make lint
	@make coverage
	@echo "\n✅ Pipeline CI simulado exitosamente!"
