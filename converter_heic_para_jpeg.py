import os
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Iterable, Tuple

from PIL import Image, ImageOps
import pillow_heif

# Regista o plugin HEIF na biblioteca Pillow
# Isto permite que o Image.open() "entenda" ficheiros .heic/.heif
pillow_heif.register_heif_opener()


def _listar_ficheiros_heic(pasta_origem: str, recursivo: bool) -> Iterable[Tuple[str, str]]:
    """
    Itera os ficheiros .heic/.heif na pasta de origem.
    Retorna tuplos (caminho_absoluto, caminho_relativo) para replicar a estrutura no destino.
    """
    exts = {".heic", ".heif"}
    pasta_origem_abs = os.path.abspath(pasta_origem)
    if recursivo:
        for raiz, _, ficheiros in os.walk(pasta_origem_abs):
            for f in ficheiros:
                if os.path.splitext(f)[1].lower() in exts:
                    caminho_abs = os.path.join(raiz, f)
                    caminho_rel = os.path.relpath(caminho_abs, pasta_origem_abs)
                    yield caminho_abs, caminho_rel
    else:
        for f in os.listdir(pasta_origem_abs):
            if os.path.splitext(f)[1].lower() in exts:
                caminho_abs = os.path.join(pasta_origem_abs, f)
                yield caminho_abs, f


def _salvar_imagem(
    caminho_entrada: str,
    caminho_saida: str,
    formato: str,
    qualidade: int,
    subsampling: int,
    progressivo: bool,
    otimizar: bool,
    manter_metadata: bool,
) -> None:
    """Abre HEIC e guarda em JPEG/PNG, preservando ICC/EXIF quando possível."""
    with Image.open(caminho_entrada) as im:
        # Corrige orientação com base no EXIF antes de converter
        im = ImageOps.exif_transpose(im)

        exif = im.info.get("exif") if manter_metadata else None
        icc = im.info.get("icc_profile") if manter_metadata else None

        if formato == "jpeg":
            params = {
                "format": "JPEG",
                "quality": qualidade,
                "subsampling": subsampling,
                "optimize": otimizar,
                "progressive": progressivo,
            }
            if exif:
                params["exif"] = exif
            if icc:
                params["icc_profile"] = icc

            # JPEG não suporta alpha; converte para RGB
            im.convert("RGB").save(caminho_saida, **params)

        elif formato == "png":
            # PNG é sem perdas; útil se pretender zero perdas (ficheiros maiores)
            params = {"format": "PNG"}
            if icc:
                params["icc_profile"] = icc
            # EXIF em PNG é pouco suportado; Pillow não escreve EXIF em PNG
            im.save(caminho_saida, **params)

        else:
            raise ValueError(f"Formato não suportado: {formato}")


def converter_heic(
    pasta_origem: str,
    pasta_destino: str,
    qualidade: int = 95,
    subsampling: int = 0,
    progressivo: bool = True,
    otimizar: bool = True,
    manter_metadata: bool = True,
    recursivo: bool = True,
    overwrite: bool = False,
    formato: str = "jpeg",
    threads: int = 0,
) -> Tuple[int, int]:
    """
    Converte HEIC/HEIF para JPEG/PNG com o mínimo de perdas possível.

    Retorna (convertidos, erros).
    """
    if not os.path.isdir(pasta_origem):
        raise FileNotFoundError(f"A pasta de origem '{pasta_origem}' não existe.")

    formato = formato.lower()
    if formato not in {"jpeg", "png"}:
        raise ValueError("'formato' deve ser 'jpeg' ou 'png'.")

    if qualidade > 95 and formato == "jpeg":
        print("Aviso: qualidade > 95 pode aumentar muito o tamanho sem ganhos visíveis.")

    pasta_origem_abs = os.path.abspath(pasta_origem)
    pasta_destino_abs = os.path.abspath(pasta_destino)
    os.makedirs(pasta_destino_abs, exist_ok=True)

    tarefas = []
    convertidos = 0
    erros = 0

    def destino_para(rel_path: str) -> str:
        nome_base, _ = os.path.splitext(rel_path)
        ext_out = ".jpg" if formato == "jpeg" else ".png"
        caminho_out = os.path.join(pasta_destino_abs, nome_base + ext_out)
        os.makedirs(os.path.dirname(caminho_out), exist_ok=True)
        return caminho_out

    ficheiros = list(_listar_ficheiros_heic(pasta_origem_abs, recursivo))
    total = len(ficheiros)
    if total == 0:
        print(f"Nenhum ficheiro .heic/.heif encontrado em '{pasta_origem}'.")
        return 0, 0

    # Define nº de threads
    if threads is None or threads <= 0:
        threads = max(1, min(32, (os.cpu_count() or 2)))

    print(f"A converter {total} ficheiro(s) de '{pasta_origem}' para '{pasta_destino}'...")
    print(
        f"Opções: formato={formato}, qualidade={qualidade}, subsampling={subsampling}, "
        f"progressivo={progressivo}, otimizar={otimizar}, manter_metadata={manter_metadata}, "
        f"recursivo={recursivo}, overwrite={overwrite}, threads={threads}"
    )

    with ThreadPoolExecutor(max_workers=threads) as executor:
        for caminho_abs, caminho_rel in ficheiros:
            saida = destino_para(caminho_rel)
            if not overwrite and os.path.exists(saida):
                # Já existe; ignora
                continue
            tarefas.append(
                executor.submit(
                    _salvar_imagem,
                    caminho_abs,
                    saida,
                    formato,
                    qualidade,
                    subsampling,
                    progressivo,
                    otimizar,
                    manter_metadata,
                )
            )

        for fut in as_completed(tarefas):
            try:
                fut.result()
                convertidos += 1
            except Exception as e:
                erros += 1
                print(f"Erro: {e}")

    print("\n--- Conversão Concluída ---")
    print(f"Ficheiros convertidos com sucesso: {convertidos}")
    print(f"Ficheiros com erro: {erros}")
    return convertidos, erros


def _parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=(
            "Converte imagens HEIC/HEIF para JPEG (quase sem perdas) ou PNG (sem perdas)."
        )
    )
    p.add_argument("--origem", default="fotos_heic", help="Pasta de origem com .heic/.heif")
    p.add_argument("--destino", default="fotos_jpeg", help="Pasta onde guardar as saídas")
    p.add_argument("--formato", default="jpeg", choices=["jpeg", "png"], help="Formato de saída")
    p.add_argument("--qualidade", type=int, default=95, help="Qualidade JPEG (1-100, recomendado 90-95)")
    p.add_argument(
        "--subsampling",
        type=int,
        default=0,
        choices=[0, 1, 2],
        help="Subamostragem de crominância JPEG: 0=4:4:4 (melhor), 1=4:2:2, 2=4:2:0",
    )
    p.add_argument("--sem-progressivo", action="store_true", help="Desativa JPEG progressivo")
    p.add_argument("--sem-otimizar", action="store_true", help="Desativa otimização de Huffman")
    p.add_argument("--sem-metadata", action="store_true", help="Não preserva ICC/EXIF")
    p.add_argument("--nao-recursivo", action="store_true", help="Não percorre subpastas")
    p.add_argument("--overwrite", action="store_true", help="Substitui ficheiros existentes no destino")
    p.add_argument("--threads", type=int, default=0, help="Nº de threads (0=auto)")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse_args(argv)
    try:
        converter_heic(
            pasta_origem=args.origem,
            pasta_destino=args.destino,
            qualidade=args.qualidade,
            subsampling=args.subsampling,
            progressivo=not args.sem_progressivo,
            otimizar=not args.sem_otimizar,
            manter_metadata=not args.sem_metadata,
            recursivo=not args.nao_recursivo,
            overwrite=args.overwrite,
            formato=args.formato,
            threads=args.threads,
        )
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
