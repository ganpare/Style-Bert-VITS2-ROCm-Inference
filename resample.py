import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import cpu_count
from pathlib import Path
from typing import Any

import numpy as np
import pyloudnorm as pyln
import soundfile
import torch
import torchaudio
import torchaudio.functional as AF
from numpy.typing import NDArray
from tqdm import tqdm

from config import get_config
from style_bert_vits2.logging import logger
from style_bert_vits2.utils.stdout_wrapper import SAFE_STDOUT


DEFAULT_BLOCK_SIZE: float = 0.400  # seconds


class BlockSizeException(Exception):
    pass


def normalize_audio(data: NDArray[Any], sr: int):
    meter = pyln.Meter(sr, block_size=DEFAULT_BLOCK_SIZE)  # create BS.1770 meter
    try:
        loudness = meter.integrated_loudness(data)
    except ValueError as e:
        raise BlockSizeException(e)

    data = pyln.normalize.loudness(data, loudness, -23.0)
    return data


def _load_audio(path: Path, target_sr: int) -> tuple[NDArray[Any], int]:
    """torchaudioを使って音声を読み込むヘルパー"""
    waveform, sr = torchaudio.load(path.as_posix())
    if waveform.dim() > 1 and waveform.size(0) > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)
    if sr != target_sr:
        waveform = AF.resample(waveform, sr, target_sr)
        sr = target_sr
    return waveform.squeeze(0).cpu().numpy(), sr



def _trim_silence(wav: NDArray[Any], top_db: float = 30.0) -> NDArray[Any]:
    """librosa.effects.trim の簡易版"""
    if wav.size == 0:
        return wav
    abs_wav = np.abs(wav)
    peak = np.max(abs_wav)
    if peak <= 0:
        return wav
    threshold = peak * (10 ** (-top_db / 20))
    idx = np.where(abs_wav > threshold)[0]
    if idx.size == 0:
        return wav
    start, end = idx[0], idx[-1] + 1
    return wav[start:end]


def resample(
    file: Path,
    input_dir: Path,
    output_dir: Path,
    target_sr: int,
    normalize: bool,
    trim: bool,
):
    """
    fileを読み込んで、target_srなwavファイルに変換して、
    output_dirの中に、input_dirからの相対パスを保つように保存する
    """
    try:
        # librosaが読めるファイルかチェック
        # wav以外にもmp3やoggやflacなども読める
        wav: NDArray[Any]
        sr: int
        wav, sr = _load_audio(file, target_sr)
        if normalize:
            try:
                wav = normalize_audio(wav, sr)
            except BlockSizeException:
                print("")
                logger.info(
                    f"Skip normalize due to less than {DEFAULT_BLOCK_SIZE} second audio: {file}"
                )
        if trim:
            wav = _trim_silence(wav, top_db=30)
        relative_path = file.relative_to(input_dir)
        # ここで拡張子が.wav以外でも.wavに置き換えられる
        output_path = output_dir / relative_path.with_suffix(".wav")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        soundfile.write(output_path, wav, sr)
    except Exception as e:
        logger.warning(f"Cannot load file, so skipping: {file}, {e}")


if __name__ == "__main__":
    config = get_config()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sr",
        type=int,
        default=config.resample_config.sampling_rate,
        help="sampling rate",
    )
    parser.add_argument(
        "--input_dir",
        "-i",
        type=str,
        default=config.resample_config.in_dir,
        help="path to source dir",
    )
    parser.add_argument(
        "--output_dir",
        "-o",
        type=str,
        default=config.resample_config.out_dir,
        help="path to target dir",
    )
    parser.add_argument(
        "--num_processes",
        type=int,
        default=4,
        help="cpu_processes",
    )
    parser.add_argument(
        "--normalize",
        action="store_true",
        default=False,
        help="loudness normalize audio",
    )
    parser.add_argument(
        "--trim",
        action="store_true",
        default=False,
        help="trim silence (start and end only)",
    )
    args = parser.parse_args()

    if args.num_processes == 0:
        processes = cpu_count() - 2 if cpu_count() > 4 else 1
    else:
        processes: int = args.num_processes

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    logger.info(f"Resampling {input_dir} to {output_dir}")
    sr = int(args.sr)
    normalize: bool = args.normalize
    trim: bool = args.trim

    # 後でlibrosaに読ませて有効な音声ファイルかチェックするので、全てのファイルを取得
    original_files = [f for f in input_dir.rglob("*") if f.is_file()]

    if len(original_files) == 0:
        logger.error(f"No files found in {input_dir}")
        raise ValueError(f"No files found in {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=processes) as executor:
        futures = [
            executor.submit(resample, file, input_dir, output_dir, sr, normalize, trim)
            for file in original_files
        ]
        for future in tqdm(
            as_completed(futures),
            total=len(original_files),
            file=SAFE_STDOUT,
            dynamic_ncols=True,
        ):
            pass

    logger.info("Resampling Done!")
