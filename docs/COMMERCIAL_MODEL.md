# MTChart SDK - Modelo Comercial

Este diretorio separa o nucleo reutilizavel do MTChart Pro para que outros
desenvolvedores possam criar sistemas parecidos com mais velocidade.

## 1. Pacote/SDK comercial

O SDK pode ser vendido como pacote privado com acesso por cliente, incluindo:

- modelos de processo, peca, pena e leitura;
- regras de validacao de temperatura e tempo;
- catalogo local reutilizavel em SQLite;
- exemplos de integracao;
- suporte e atualizacoes por periodo contratado.

## 2. Base gratuita + camada paga

Uma estrategia viavel e manter uma versao de avaliacao ou uma API reduzida e
cobrar pelos recursos que mais entregam valor:

- geracao profissional de PDF e Excel;
- conectores com equipamentos industriais;
- dashboard web/cloud;
- templates de sistemas prontos;
- suporte tecnico e implantacao assistida;
- licenca para uso comercial em produtos de terceiros.

## Separacao recomendada

- `mtchart_sdk`: nucleo tecnico reutilizavel.
- `examples`: demonstracoes simples para desenvolvedores.
- produto pago: relatorios, interface, conectores, automacoes e suporte.

Essa separacao permite publicar, vender ou licenciar o SDK sem expor todo o
aplicativo desktop.
