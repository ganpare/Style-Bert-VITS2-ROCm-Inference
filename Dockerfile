# ベースイメージとして、ROCm 7.1とPyTorch 2.8.0を含む公式イメージを使用
# PyTorch 2.8.0はStyle-Bert-VITS2の要件(torch<2.4)を満たさないため、このDockerfileは実験的なものとなる
FROM rocm/pytorch:rocm7.1_ubuntu24.04_py3.12_pytorch_release_2.8.0

# 作業ディレクトリの設定
WORKDIR /app

# Style-Bert-VITS2のソースコードをコンテナ内にコピー
COPY . /app/Style-Bert-VITS2
WORKDIR /app/Style-Bert-VITS2

# 依存関係のインストール
# requirements.txtからtorchとtorchaudioの行を削除し、残りの依存関係をインストール
# PyTorch 2.8.0はtorch<2.4の要件を満たさないため、このアプローチで試行する
# また、numpy<2 の要件を PyTorch 2.8.0 と互換性のあるバージョンに修正
RUN sed -i '/torch/d' requirements.txt && \
    sed -i '/torchaudio/d' requirements.txt && \
    sed -i 's/numpy<2/numpy==1.26.4/' requirements.txt

# pipのアップグレードと依存関係のインストール
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 環境変数の設定（ROCm関連はベースイメージで設定済みだが、念のため）
ENV PATH="/opt/rocm/bin:${PATH}"

