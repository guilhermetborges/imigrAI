# imigrAI - Documentação Técnica Consolidada

Esta pasta centraliza a documentação do projeto com foco em arquitetura, regras de negócio e operação.

## Índice

- [01. Visão do Projeto](./01-visao-do-projeto.md)
- [02. Arquitetura da Solução](./02-arquitetura-da-solucao.md)
- [03. Backend (FastAPI + Domínios)](./03-backend-fastapi-dominios.md)
- [04. Frontend (Next.js App Router)](./04-frontend-nextjs.md)
- [05. Modelo de Dados e Migrações](./05-modelo-de-dados-migracoes.md)
- [06. Regras de Negócio](./06-regras-de-negocio.md)
- [07. Fluxos E2E e Contratos de API](./07-fluxos-e2e-e-contratos-api.md)
- [08. Operação, Deploy e Observabilidade](./08-operacao-deploy-observabilidade.md)
- [09. Testes e Qualidade](./09-testes-e-qualidade.md)

## Escopo

A documentação foi construída diretamente a partir do código-fonte atual do repositório (backend, frontend, migrations, scripts e testes), refletindo o comportamento implementado.

## Convenções rápidas

- `Free`: usuário com entitlements mínimos e quota mensal de assessments.
- `Pro`: usuário com entitlements ampliados, roadmap IA e prioridade de processamento.
- `Assessment`: cálculo de score de elegibilidade por regras dinâmicas.
- `Roadmap`: plano de ação priorizado, gerado a partir do resultado de assessment.
- `Ingestão`: pipeline de atualização de fontes oficiais (bronze/silver/publicação).

