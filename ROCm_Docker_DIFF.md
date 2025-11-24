# ROCm Docker対応差分メモ (docker-setup ブランチ)

このドキュメントは `master` ブランチから分岐した `docker-setup` worktree で行った変更点をまとめたものです。ROCm 7.1 環境で Style-Bert-VITS2 を動作させるための Docker 対応と、それに付随する依存関係の整理を中心に記録しています。

## 1. Dockerfile の追加
- ベースイメージ: `rocm/pytorch:rocm7.1_ubuntu24.04_py3.12_pytorch_release_2.8.0` (digest: `sha256:3e917342...`)
- 作業ディレクトリ `/app/Style-Bert-VITS2` にソースをコピーし、`requirements.txt` から `torch/torchaudio` を削除した後に `numpy==1.26.4` を固定して依存をインストール。
- 生成されたイメージタグ: `style-bert-vits2-rocm:7.1`

## 2. Python 3.12 環境向けの依存関係整理
- `requirements*.txt` から Python 3.12 でビルド不可なライブラリ (`librosa`, `stable_ts`, `umap-learn`, `pyannote.audio`, `onnx`, `onnxconverter-common`, `onnxsim` など) を除外。
- `kiwisolver>=1.4.7`, `fonttools>=4.60.0`, `contourpy>=1.2.0`, `cycler>=0.12.1`, `tensorboard==2.14.0` などを追加し、pip の解決が安定するように固定。
- `onnxruntime` のみ残している (推論で使用)。ONNX 変換スクリプトを実行する場合は手動で `onnx`, `onnxconverter-common`, `onnxsim` をインストールする運用。

## 3. `librosa` 依存の排除
- `resample.py`
  - 読み込み・リサンプリングを `torchaudio` + `torchaudio.functional.resample` に置き換え。
  - `librosa.effects.trim` 相当の簡易サイレンス除去 `_trim_silence` を実装。
- `mel_processing.py`
  - mel フィルタ生成を `librosa` から `torchaudio.functional.create_fb_matrix` に置き換え。
  - `torch` テンソルでメルスペクトログラム計算を完結。

## 4. UMAP → PCA への変更
- `gradio_tabs/style_vectors.py`: `umap-learn` 依存を削除し `sklearn.decomposition.PCA` で 2 次元可視化。

## 5. 任意機能の ImportError ガイド
- `style_gen.py`: `pyannote.audio` が未導入の場合に明示的に ImportError を出すよう `try/except` でガード。
- `convert_onnx.py` / `convert_bert_onnx.py`: `onnx`/`onnxconverter-common`/`onnxsim` がない場合にわかりやすいメッセージで案内するよう変更。

## 6. Docker実行環境の整備
- `docker-compose.yml` を追加: ROCmデバイス（`/dev/kfd`, `/dev/dri`）のマウントと環境変数設定を含む構成。
- `run_rocm_docker.sh` を追加: ROCmデバイスアクセス用のdocker run実行スクリプト。
  - 自動イメージビルド機能
  - ボリュームマウント（`model_assets`, `inputs`, `outputs`）
  - 環境変数設定（`HSA_OVERRIDE_GFX_VERSION=11.0.0` など）

## 7. ドキュメント整備
- `README.md` に「ROCm Docker環境での実行」セクションを追加:
  - Dockerイメージのビルド手順
  - docker-composeとdocker runの両方の実行方法
  - オプショナル依存関係（`pyannote.audio`, ONNX変換ツール）のインストール手順
  - 注意事項とトラブルシューティング

## 8. 詳細ドキュメントの追加
- `DOCKER_USAGE.md` を追加: ROCm Docker環境の詳細な使用方法、トラブルシューティング、パフォーマンス最適化などを含む包括的なガイド。
- `QUICKSTART_DOCKER.md` を追加: 推論直前までセットアップするためのクイックスタートガイド。

## 9. モデル初期化機能の追加
- `init_docker.sh` を追加: Docker環境で `initialize.py` を実行して推論用モデルをダウンロードするスクリプト。
  - `--only_infer` オプションで推論用モデルのみダウンロード（デフォルト）
  - `--full` オプションで学習用モデルも含めてダウンロード
  - `--skip-default` オプションでデフォルトモデルのダウンロードをスキップ
- `docker-compose.yml` と `run_rocm_docker.sh` に必要なボリュームマウント（`bert/`, `slm/`, `pretrained/` など）を追加。

## 10. 現時点の TODO
- ROCm デバイスをマウントした `docker run` での動作確認 (未実施)。
- 実際のROCm環境でのGPU認識・動作テスト。
- 各種スクリプト（`app.py`, `server_editor.py`, `server_fastapi.py`）での動作確認。

---
このファイルを更新しながら `docker-setup` ブランチ専用の差分メモとして利用してください。
