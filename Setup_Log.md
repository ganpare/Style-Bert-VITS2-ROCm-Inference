# GMKtec EVO-X2 (Ryzen AI Max+ 395) AI推論環境構築ログ

**Target:** Style-Bert-VITS2 on Ubuntu 24.04 LTS (ROCm 7.1)

**構築日:** 2025年11月23日

**Status:** ✅ 構築完了

---

## 1. マシンスペック & BIOS設定

* **Model:** GMKtec EVO-X2
* **APU:** AMD Ryzen AI Max+ 395 (16C/32T) / Radeon 8060S (Strix Halo / gfx1151)
* **OS:** Ubuntu 24.04.3 LTS
* **Kernel:** 6.14.0-1016-oem (OEMカーネル)
* **重要BIOS設定:**
    * `UMA Frame Buffer Size`: **64GB** (または最大値)
    * ※ AI処理のためにVRAMを減らさず、メインメモリからガッツリ割り当てること。

---

## 2. システム・ドライバ導入 (ROCm 7.1)

Strix Haloを正式サポートする最新ドライバを導入する。ただし、**LightDM/VNC環境を守るため、描画ドライバは上書きしない。**

### 2-1. カーネルと必須ライブラリの準備

```bash
# OEMカーネルの導入 (Strix Halo対応のため)
sudo apt update && sudo apt-get install linux-oem-24.04c -y
sudo reboot

# FFmpeg/Audio関連の開発ライブラリ (ビルドエラー回避用)
sudo apt install -y pkg-config libavcodec-dev libavformat-dev libavdevice-dev \
libavutil-dev libavfilter-dev libswscale-dev libswresample-dev build-essential
```

### 2-2. ROCm 7.1 インストール

**注意:** `--usecase=rocm` のみ指定し、`graphics` は指定しないこと（ブラックスクリーン回避）。

```bash
# インストーラー取得
wget https://repo.radeon.com/amdgpu-install/7.1/ubuntu/noble/amdgpu-install_7.1.70100-1_all.deb
sudo apt install ./amdgpu-install_7.1.70100-1_all.deb

# インストール実行 (GUIドライバ非干渉モード)
sudo amdgpu-install -y --usecase=rocm --no-dkms

# 権限付与
sudo usermod -a -G render,video $USER
sudo reboot
```

*確認:* `rocminfo | grep gfx` で `gfx1151` が見えれば成功。

**現在の状態:**
- ROCm 7.1 インストール済み
- gfx1151 (Strix Halo) 認識確認済み
- マーケティング名: AMD RYZEN AI MAX+ 395 w/ Radeon 8060S

---

## 3. Python環境構築 (uv)

Condaよりも高速・軽量な `uv` を使用する。

### 3-1. uv インストール

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

**現在の状態:**
- uv 0.9.10 インストール済み
- パス: `/home/sungo/.local/bin/uv`

### 3-2. プロジェクトセットアップ

```bash
git clone https://github.com/litagin02/Style-Bert-VITS2.git
cd Style-Bert-VITS2

# Python 3.10 環境作成
uv venv --python 3.10
source .venv/bin/activate
```

**現在の状態:**
- Python 3.10.19 環境作成済み
- 仮想環境: `.venv/` (UV管理)
- プロジェクトディレクトリ: `/home/sungo/Style-Bert-VITS2`

---

## 4. 依存関係の解消 (魔改造編)

Ubuntu 24.04のライブラリとROCm環境に合わせるため、`requirements.txt` を修正する。

### 4-1. requirements.txt の修正

`nano requirements.txt` で以下の箇所を変更・コメントアウトする。

1. **PyTorch系のバージョン指定を無効化** (ROCm版を守るため)
    ```text
    # torch<2.4
    # torchaudio<2.4
    ```

2. **ONNX GPU版を無効化** (CUDA用が入るのを防ぐため)
    ```text
    # onnxruntime-gpu; sys_platform != 'darwin'
    ```

3. **古いライブラリのバージョン固定を解除** (ビルドエラー回避)
    * `faster-whisper==0.10.1` → `faster-whisper`
    * `librosa==0.9.2` → `librosa`

**現在の状態:**
- `requirements.txt` 修正済み
- PyTorch関連のバージョン指定コメントアウト済み
- ONNX GPU版コメントアウト済み

### 4-2. インストール実行

```bash
# 一括インストール
uv pip install -r requirements.txt

# 【最重要】ROCm版 PyTorch で上書き確定
# ※ これを最後にやらないと標準のtorchが入ってGPUが動かない
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.2
```

**現在の状態:**
- ✅ 主要依存関係インストール済み
  - gradio, transformers, onnxruntime, accelerate 等
- ✅ PyTorch ROCm版インストール済み
  - PyTorch: 2.5.1+rocm6.2
  - ROCm version: 6.2.41133-dd7f95766
  - CUDA available: True (ROCm環境でTrueと表示)
  - Device count: 1

---

## 5. アプリケーション起動

Radeon 8060S (gfx1151) を PyTorch に認識させるための「擬態コマンド」を使って起動する。

```bash
# 環境変数 HSA_OVERRIDE_GFX_VERSION=11.0.0 を付与
HSA_OVERRIDE_GFX_VERSION=11.0.0 python app.py
```

* **Access:** `http://localhost:7860`
* **Check:** ログに `device: cuda` (AMDでもPyTorch上はこう表示される) と出ればGPU動作成功。

**起動コマンド例:**
```bash
cd /home/sungo/Style-Bert-VITS2
source .venv/bin/activate
HSA_OVERRIDE_GFX_VERSION=11.0.0 python app.py
```

---

## 6. トラブルシューティング

* **画面が真っ暗になった:**
    * SSHで入り `sudo amdgpu-install --uninstall` でドライバ削除後、再起動。インストール時に `--usecase=graphics` を外しているか再確認。

* **av/FFmpegのエラー:**
    * `sudo apt install libavcodec-dev ...` などのシステムライブラリが入っているか確認。
    * `requirements.txt` で `faster-whisper` のバージョン指定を外したか確認。

* **PyTorchがGPUを認識しない:**
    * `HSA_OVERRIDE_GFX_VERSION=11.0.0` 環境変数を必ず設定する
    * `rocminfo | grep gfx` でgfx1151が表示されることを確認
    * `python -c "import torch; print(torch.cuda.is_available())"` でTrueになることを確認

---

## 7. 環境確認コマンド

### GPU認識確認
```bash
rocminfo | grep -E "(gfx|Marketing)"
```

### PyTorch確認
```bash
source .venv/bin/activate
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}')"
```

### 主要パッケージ確認
```bash
source .venv/bin/activate
python -c "import gradio; import transformers; import onnxruntime; print('主要パッケージ: OK')"
```

---

## 8. 次のステップ

1. **モデルの初期化:**
   ```bash
   source .venv/bin/activate
   python initialize.py  # 必要なモデルとデフォルトTTSモデルをダウンロード
   ```

2. **エディター起動:**
   ```bash
   source .venv/bin/activate
   HSA_OVERRIDE_GFX_VERSION=11.0.0 python server_editor.py --inbrowser
   ```

3. **学習開始:**
   - データセット準備後、`Train.bat` または `python app.py` の学習タブから開始

---

## まとめ

このマシン特有の「罠（GUI競合、PyTorch認識、依存関係の衝突）」をすべて回避した**完全攻略マニュアル**です。

**構築完了項目:**
- ✅ ROCm 7.1 ドライバ導入
- ✅ UV環境構築 (Python 3.10.19)
- ✅ 依存関係インストール
- ✅ PyTorch ROCm版 (2.5.1+rocm6.2) インストール
- ✅ GPU認識確認 (gfx1151)

今後のメンテナンスや再構築の際に役立ててください。

---

**構築完了日:** 2025年11月23日  
**環境:** Ubuntu 24.04.3 LTS / ROCm 7.1 / UV 0.9.10 / PyTorch 2.5.1+rocm6.2

