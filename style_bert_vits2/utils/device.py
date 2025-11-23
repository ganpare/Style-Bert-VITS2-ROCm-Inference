"""
デバイス検出と管理に関するユーティリティ関数

ROCmとCUDAの両方に対応したデバイス検出機能を提供します。
"""
from __future__ import annotations

try:
    import torch
except ImportError:
    torch = None  # type: ignore


def is_gpu_available() -> bool:
    """
    GPU（CUDAまたはROCm）が利用可能かどうかを判定する

    Returns:
        bool: GPUが利用可能な場合True
    """
    if torch is None:
        return False
    
    # CUDAが利用可能か
    if hasattr(torch, "cuda") and torch.cuda.is_available():
        return True
    
    # ROCmが利用可能か（torch.version.hipが存在する場合はROCm環境）
    if hasattr(torch.version, "hip") and torch.version.hip is not None:
        # ROCm環境では、デバイスが利用可能かチェック
        try:
            if torch.cuda.is_available():
                return True
        except Exception:
            pass
    
    return False


def get_default_device() -> str:
    """
    デフォルトのデバイスを取得する
    CUDAが利用可能な場合は "cuda"、ROCmのみの場合は "cuda"（ROCmはcuda互換）、
    それ以外は "cpu" を返す

    Returns:
        str: デバイス名（"cuda", "cpu"など）
    """
    if is_gpu_available():
        return "cuda"
    return "cpu"


def is_rocm_environment() -> bool:
    """
    ROCm環境かどうかを判定する

    Returns:
        bool: ROCm環境の場合True
    """
    if torch is None:
        return False
    
    # ROCm環境では torch.version.hip が設定される
    return hasattr(torch.version, "hip") and torch.version.hip is not None


def clear_gpu_cache() -> None:
    """
    GPUキャッシュをクリアする
    CUDAとROCmの両方に対応
    """
    if torch is None:
        return
    
    if is_gpu_available():
        try:
            torch.cuda.empty_cache()
        except Exception:
            # ROCm環境でもtorch.cuda.empty_cache()は動作するが、
            # 念のため例外処理を追加
            pass


def normalize_device(device: str) -> str:
    """
    デバイス名を正規化する
    ROCm環境では "cuda" として扱われるが、明示的に "rocm" が指定された場合も対応

    Args:
        device (str): 元のデバイス名

    Returns:
        str: 正規化されたデバイス名
    """
    if device.startswith("rocm"):
        # ROCm環境では "rocm:0" を "cuda:0" に変換（PyTorchではROCmもcudaとして扱われる）
        if ":" in device:
            device_id = device.split(":")[1]
            return f"cuda:{device_id}"
        return "cuda"
    
    return device
