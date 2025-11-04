# Conversor HEIC para JPEG/PNG (qualidade máxima)

Este script converte imagens HEIC/HEIF para JPEG com perdas mínimas (4:4:4, qualidade 95, progressivo, otimização) ou para PNG sem perdas.

## Requisitos

- Python 3.9+
- Windows, macOS ou Linux

Instale as dependências:

```powershell
# No PowerShell
python -m pip install -r requirements.txt
```

## Utilização

Por omissão, lê de `fotos_heic/` e escreve em `fotos_jpeg/`, de forma recursiva.

```powershell
python .\converter_heic_para_jpeg.py
```

Opções principais:

```powershell
python .\converter_heic_para_jpeg.py `
  --origem fotos_heic `
  --destino fotos_jpeg `
  --formato jpeg `            # ou png (sem perdas)
  --qualidade 95 `            # 1-100 (recomendado 90-95)
  --subsampling 0 `           # 0=4:4:4 (melhor), 1=4:2:2, 2=4:2:0
  --overwrite `               # sobrescrever se já existir
  --nao-recursivo `           # se NÃO quer percorrer subpastas
  --sem-progressivo `         # desativa JPEG progressivo
  --sem-otimizar `            # desativa otimização de Huffman
  --sem-metadata `            # não preserva ICC/EXIF
  --threads 0                 # 0=auto, ou um número (ex.: 8)
```

## Dicas de qualidade

- Para JPEG com perdas mínimas: use `--qualidade 95 --subsampling 0` (4:4:4), mantendo `progressivo` e `otimizar` ativos.
- Para zero perdas, use `--formato png` (ficheiros maiores).
- O script preserva ICC e EXIF quando possível; a orientação é corrigida automaticamente.
- HEIC HDR (10-bit) será convertido para 8-bit, pois JPEG/PNG comum é 8-bit.

## Estrutura de pastas

- `fotos_heic/` — entrada (pode conter subpastas)
- `fotos_jpeg/` — saída (estrutura replicada)

## Licença e autoria

- Licença: MIT
- Autor: Carlos Araújo

## Problemas comuns

- Se vir erro de import `pillow_heif`, confirme a instalação de dependências e reinicie o Python/VS Code.
- Alguns ficheiros HEIC proprietários podem falhar; tente atualizar as bibliotecas para a versão mais recente.
