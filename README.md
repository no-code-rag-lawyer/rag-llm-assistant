# 第１　プロジェクト概要

本プログラムは、NAS内のファイルを自動探索し、内部に存在するワードエクセルPDF（Calendarは予定）を自動的にテキスト化、チャンク化、ベクトルDBに登録の上、LLMに対する質問に対して、RAG検索を行い、その回答を参考にLLMが回答を行うシステムである。

本プログラムは、当職が、①過去の事件記録の探索、過去の事件記録における主張、過去の事件記録における相手方の主張等を探索することと、②自己の主張及び相手方の主張の論理飛躍、矛盾主張の探索に使用することを目的として作成した。

上記①からは、ベクトルDBに登録されたファイルの所在地とNAS内のファイルの所在地が異なることは許されず、絶対パスをチャンク化することによりそれを実現した。

ただし、②については、本プログラムではあまり達成できないことが現時点において判明している。

今後の課題

Calendarとの連携（今はまだ、テキスト生成スクリプトを作成していない）

LLMに対する質問に対するシステムプロンプトについて、その改変、追加、削除の容易性を上昇させる。

LLMに対する質問RAG検索を行うか否か、行うとして引用か参考とすべきかを任意に変更できるようにする

ウェイクアップワードの導入

その他気づいたこと（スクリプトの分離）

# 第２　主たる機能

１　ワード、エクセル、PDFの自動テキスト化、及びPDFについては、当該PDFにテキストが埋め込まれていないなら、OCRで埋め込み処理を行う（ただしタイムスタンプは変更しない。）

２　テキスト化後、チャンク化、ベクトルDBに登録

３　FirstAPI経由で、ChatUIと連携、なお音声入力については、現在ボタン式であり、ウェイクアップワードの待受は以降の実装予定

４　LLMモデル及び、システムプロンプトの動的変更、システムプロントは、テキストファイルであり、改変追加が容易であること（UIによる変更、登録、削除は未実装）

# 第３　技術面について

✅ 主要技術

本システムは、RAG（Retrieval-Augmented Generation）＋LLM統合を中心に、
音声入出力・ファイルOCR処理・カレンダー連携（予定）までを含む分割コンテナ構成です。



1. Web / API 基盤（/fastapi コンテナ）

FastAPI：非同期対応の軽量Webフレームワーク

Uvicorn：ASGIサーバ（FastAPI実行用）

Pydantic：APIリクエスト/レスポンスのスキーマ定義・バリデーション

httpx / requests：LLM・VOICEVOXなど外部API呼び出し

python-dotenv：環境変数管理

python-multipart / aiofiles：ファイルアップロードや非同期ファイルI/O

tiktoken：LLMトークン長計算（コンテキスト制御用）



2. ベクトルDB / RAG 基盤（/vector コンテナ）

ChromaDB：RAG検索用ベクトルデータベース

sha256＋インデックス＋再生成方式：ゴースト検出・再同期対応の堅牢設計

メタ情報ベクトル化：ファイル名・更新日時などを含めた検索精度向上



3. 音声処理 / 音声認識（/fastapi & /voicevox コンテナ）

Faster-Whisper：Whisper高速版による音声入力

WebRTC VAD（webrtcvad）：音声区間検出

sounddevice / pydub / pyaudio：マイク入力・音声ファイル処理

VOICEVOX Engine（公式CPU版、Dockerfile不要）：音声合成エンジン
　- Port：50021（FastAPIからAPI呼び出し）
　- Network：secretary-net（他コンテナとブリッジ共有）



4. フロントエンド（/firstapi コンテナ）

HTML / JavaScript / CSS（Nginx配信）

動的プロンプト編集・モデル切替（UI上でリアルタイム制御可能）



5. LLM推論基盤（LLMコンテナ）

llama-cpp-python：ローカルLLM推論（LLaMA系、CPU/NPU対応可）

transformers / huggingface_hub：Hugging Faceモデル互換＆管理

sentencepiece：Gemma・LLaMA系トークナイザー

torch / numpy：推論最適化、数値計算基盤



6. RAG処理・ファイル前処理基盤（RAG処理コンテナ）

OCR / PDF・画像処理：
　- Pytesseract / PaddleOCR（高精度OCR、バージョン固定で安定運用）
　- pdf2image / pdfminer.six / PyMuPDF / PyPDF2（PDF解析）
　- piexif（画像EXIF活用）

Officeファイル処理：
　- python-docx（Word）、openpyxl / xlrd / pandas（Excel）、natsort（自然順ソート）

チャンク化・ベクトル化：
　- sentence-transformers / transformers / sentencepiece（埋め込み生成）
　- scikit-learn / numpy（類似度計算補助）、tqdm（進捗表示）

カレンダーAPI連携：
　- google-api-python-client / google-auth(-oauthlib)（Googleカレンダー）
　- icalendar / icalevents（iCal形式、Synology対応）

### 埋め込みモデル

- **legal-bge-m3**（Hugging Face: "legal-bge-m3"）  
- **ruri-v3-310m**（Hugging Face: "cl-nagoya/ruri-v3-310m"）  
- **形式**：SentenceTransformers形式（safetensors版推奨）  
- **配置先**：
  ```
  /mydata/llm/vector/models/
    ├── legal-bge-m3/
    └── ruri-310m/
  ```

- **取得例（Python）**：
  ```python
  from sentence_transformers import SentenceTransformer
  model = SentenceTransformer("legal-bge-m3", cache_folder="/mydata/llm/vector/models/")

処理対象ファイルの保存先

「RAG化対象は/mydata/nas/に置く」


7. コンテナ運用 / インフラ

Docker / Portainer：コンテナ分割運用（スタック推奨）

ブリッジネットワーク secretary-net：全コンテナ共通通信網

再起動ポリシー restart: always：堅牢構成

# 第４　環境要件

OS: Linux（Ubuntu 20.04 / 22.04 推奨）

※ Windows / macOS でも Docker が動けば可

CPU: x86_64 / ARM64（llama-cpp-python がビルドできる環境）

メモリ: 16GB 以上推奨（RAG＋LLM同時利用時）

Docker: 20.x 以上

Portainer（任意）: スタック運用推奨

（作成コンテナは下記の通り

Firstapi

（全コンテナの司令部、RAG検索、LLM推論呼び出し、VOICEVOX呼び出し、UIとの通信すべてを束ねる）

Jupiter（開発用コピペ貼り付け用）

Llama（推論LLM登録）

Portainer（コンテナ管理）

Vector（RAGデータベース登録）

VOICEVOX音声呼び出し

GPU（任意）: LLM推論でPyTorchを使う場合にのみ推奨

※「知らんけど、これくらいあれば動くはず」というレベルの目安です。



✅ インストール手順

1. リポジトリ取得

bash

コードをコピーする

git clone https://github.com/yourname/your-repo.git

cd your-repo

2. コンテナ起動

Portainer推奨の場合

「スタック追加」

docker-compose.yml をそのまま貼り付け

「デプロイ」を押すだけ

CLIで起動する場合

bash

コードをコピーする

docker-compose up -d

3. 初回起動後の確認

FastAPI: http://localhost:8000/docs

VOICEVOX: http://localhost:50021（API動作確認用）

UI: http://localhost:8080

（ただし、簡略化しているので、保証はしない）
追記
### 埋め込みモデル
- **legal-bge-m3**（Hugging Face: "legal-bge-m3"）
- 形式：SentenceTransformers形式（safetensors版推奨）
- 配置先：
  /mydata/llm/vector/models/
    ├── legal-bge-m3/
    └── ruri-310m/
- Hugging Faceからの取得例：
  ```python
  from sentence_transformers import SentenceTransformer
  model = SentenceTransformer("legal-bge-m3", cache_folder="/mydata/llm/vector/models/")

# 第５　使用方法

１　/mydata/nas/に、ファイルをいれる

/mydata/llm/vector/script/run_all_pipeline.pyを叩く

（ベクトル登録完了）

２　https:// localhost:8000/で、UIに入れる



# 第６　構成

/mydata/llm/

├── fastapi/            # ★ firstAPIコンテナ（全体統括）

│   ├── chat_logs/      # 会話ログ・グローバル設定保存

│   ├── config/         # 環境設定・プロンプト類

│   ├── routers/        # APIルーター（LLM・RAG・音声連携）

│   ├── static/         # UI用の静的ファイル

│   ├── docker-compose.yml

│   ├── Dockerfile

│   ├── main.py         # FastAPIエントリーポイント

│   └── entrypoint.sh   # コンテナ起動スクリプト

│

├── llama/              # ★ LLM推論コンテナ用データ

│   └── models/         # Gemma / Shisa などLLaMA系モデル格納

│

├── vector/             # ★ RAG基盤（ベクトルDB & 前処理）

│   ├── db/

│   │   ├── chroma/     # ChromaDB本体

│   │   ├── chunk/      # チャンクファイル（word/pdf/excel/calendar）

│   │   ├── log/        # UIDログ、削除ログ

│   │   └── text/       # 生テキスト格納

│   ├── models/         # 埋め込みモデル（legal-bge-m3 / ruri-310m）

│   └── script/         # RAG処理スクリプト群

│

├── voicevox/           # ★ VOICEVOXコンテナ（音声合成エンジン）

│

└── nas/                # NASマウント領域（PDF/Word/Excel 原本保管）

# 第７　ライセンス、免責事項

１、個人使用・改変等は自由です。

２、商用利用は禁止します。

３、作者は一切の責任を負いません。

４，作者への質問は自然言語を用いたものに限ります。（技術的詳細は聞かれても答えられません）

５，その他、予告なく変更・削除する場合があります。

# 第８　作者について

１　私は、一弁護士です。

個人的に準備書面、判決文などをLLMに投げて論理飛躍、論理矛盾を出せれば良いかと作成を開始しましたが、RAG化することなく、コンテキストとしてLLMに投げれば良いだけでしたが、まぁ作成後に理解しました。

それでも、条文については法令APIがあること、過去の資料の探索には、便利になるのではと考えて、今般とりあえず作成してみたという状況です。

２　次に、当職、コードが１行も書けませんし、読めません。

（HPも作ったことありませんし、Pythonなにそれのレベルです。）

故に、このスクリプト群の作成者は、ChatGPT４oです。

したがいまして、技術的側面について、当職に釈明を求められましても、お答えは、「ChatGPTに聞いて下さい」となります。

以上