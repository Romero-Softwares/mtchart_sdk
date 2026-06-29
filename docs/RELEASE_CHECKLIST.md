# MTChart SDK - Checklist de Release

Use este checklist antes de entregar o SDK para um cliente, publicar um pacote
privado ou gerar uma versao comercial.

## Validacao tecnica

- Atualizar `version` em `pyproject.toml`.
- Confirmar `project.urls` apontando para `https://github.com/Romero-Softwares/mtchart_sdk`.
- Conferir `README.md`, `LICENSE.md`, `docs/COMMERCIAL_MODEL.md` e exemplos.
- Conferir `DEPLOY.md` antes de enviar para GitHub ou PyPI.
- Rodar `python tools/validate_release.py` dentro da pasta `sdk`.
- Gerar artefatos com `python -m build` quando o pacote `build` estiver instalado.
- Conferir artefatos com `python -m twine check dist/*` quando o pacote `twine` estiver instalado.
- Testar instalacao local em ambiente limpo com `python -m pip install -e .`.
- Executar `mtchart-sdk-demo --value 188.7` apos a instalacao.

## Limpeza antes de distribuir

- Nao incluir bancos locais `*.db`.
- Nao incluir `__pycache__`, `.pytest_cache`, `build`, `dist` ou `*.egg-info`.
- Nao publicar chaves, tokens, historicos de cliente ou dados reais de processo.
- Conferir se os exemplos usam dados ficticios.

## Entrega comercial

- Definir se a entrega sera por repositorio privado, pacote wheel, contrato ou area de cliente.
- Informar claramente limites de uso, suporte, atualizacoes e direito de revenda.
- Separar recursos premium como conectores industriais, relatorios profissionais e dashboard cloud.

## Deploy

- Usar `https://github.com/Romero-Softwares/mtchart_sdk` como repositorio do SDK.
- Fazer o primeiro push a partir da pasta `sdk`, nao da raiz do aplicativo desktop.
- Criar tag `v0.1.0` somente depois que a validacao local estiver verde.
- Configurar `PYPI_API_TOKEN` e ambiente `pypi` no GitHub apenas quando a publicacao no PyPI for autorizada.
