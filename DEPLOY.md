# Deploy do MTChart SDK

Repositorio de destino:

```text
https://github.com/Romero-Softwares/mtchart_sdk
```

## 1. Validacao local

Rode dentro da pasta `sdk`:

```powershell
python tools\validate_release.py
python -m build
```

O primeiro comando valida metadados, compilacao, testes, exemplo e CLI. O
segundo gera `dist/*.whl` e `dist/*.tar.gz`.

## 2. Primeiro envio para o GitHub

Se a pasta `sdk` ainda nao for um repositorio Git separado:

```powershell
git init
git branch -M main
git remote add origin https://github.com/Romero-Softwares/mtchart_sdk.git
git add .
git commit -m "Prepare MTChart SDK release package"
git push -u origin main
```

Se o repositorio ja existir localmente, use:

```powershell
git remote set-url origin https://github.com/Romero-Softwares/mtchart_sdk.git
git add .
git commit -m "Prepare MTChart SDK release package"
git push
```

## 3. Criar release no GitHub

Depois do push:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

O workflow `.github/workflows/release.yml` roda testes, cria os artefatos do
pacote e anexa `dist/` como artifact da acao.

## 4. Publicar no PyPI depois

Antes de publicar:

- revisar `LICENSE.md` e confirmar o modelo comercial;
- confirmar se o nome `mtchart-sdk` esta disponivel no PyPI;
- criar uma conta no PyPI;
- gerar um API token;
- salvar o token em `Settings > Secrets and variables > Actions` com o nome
  `PYPI_API_TOKEN`;
- publicar preferencialmente a partir de uma release/tag revisada.

Publicacao manual:

```powershell
python -m pip install --upgrade build twine
python -m build
python -m twine check dist/*
python -m twine upload dist/*
```

