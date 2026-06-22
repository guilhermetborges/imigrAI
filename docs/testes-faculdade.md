# Testes do Projeto

## Objetivo
Validar o projeto localmente com SQLite e armazenamento em memoria, sem Supabase e sem Redis.

## Banco Local
- Arquivo SQLite: `data/imigrai.db`.
- O backend cria as tabelas automaticamente ao iniciar em ambiente local.
- Arquivos brutos da ingestao ficam em `.cache/ingestion`.

## Testes Unitarios
Backend:

```bash
pytest --cov=app --cov=apps --cov-report=term-missing --cov-report=xml
```

Frontend:

```bash
cd frontend
npm test
```

## Sonar
Gerar cobertura antes da analise:

```bash
pytest --cov=app --cov=apps --cov-report=xml
```

Rodar SonarScanner local:

```bash
sonar-scanner
```

O arquivo `sonar-project.properties` ja aponta para `coverage.xml` no backend e `frontend/coverage/lcov.info` se a cobertura do frontend for habilitada depois.

## Teste Manual
1. Instalar dependencias: `pip install -e .[dev]`.
2. Copiar `.env.example` para `.env` se necessario.
3. Iniciar API: `uvicorn app.main:app --reload`.
4. Abrir `http://127.0.0.1:8000/docs`.
5. Validar `GET /health/live` retorna `200`.
6. Validar `GET /health/ready` retorna `200`.
7. Executar um fluxo principal pela Swagger UI e confirmar que os dados persistem em `data/imigrai.db`.
