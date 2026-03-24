# Universal Audio Visualizer

オーディオファイルをフルHD/60fpsのスペクトラム動画へ変換するクロスプラットフォームツールです。

## 特徴
- `01_Input` 配下の音源をまとめて変換
- 変換に使った元音源は `04_Archive/実行日時/` へ自動退避
- FFmpegを自動取得して `bin/` に配置
- 日本語ファイル名テロップ対応（安全化/長さ調整あり）
- 低優先度モード、完了後フォルダ展開、スリープ
- Windows/macOS 向けの「Python未導入対応ランチャー」同梱

## Python 未導入PCでの実行
### Windows
1. `start.bat` を実行
2. 初回は `uv` と Python 3.11 を `.runtime/` に自動構築
3. 依存パッケージを固定バージョンで同期後、GUI起動

### macOS
1. `chmod +x start.command` を一度実行
2. `./start.command` を実行
3. 初回は `uv` と Python 3.11 を `.runtime/` に自動構築
4. 依存パッケージを固定バージョンで同期後、GUI起動

この方式により、システムPythonやグローバルモジュールに依存せず、バージョン差分問題を避けられます。

## 開発者向けCLI
- 初期化のみ: `python converter.py --init-only`
- CLI変換: `python converter.py --low-priority --no-open-folder`
- GUI起動: `python converter.py --gui`

## ディレクトリ
- `01_Input/`: 入力音源
- `02_Processing/`: 一時処理（終了時に掃除）
- `03_Output/`: 出力動画
- `04_Archive/`: 変換後に退避した元音源
- `logs/`: ログ
