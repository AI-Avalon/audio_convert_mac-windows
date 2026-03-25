# Universal Audio Visualizer

オーディオファイルをフルHD/60fpsのスペクトラム動画へ変換するクロスプラットフォームツールです。

## 特徴
- `01_Input` 配下の音源をまとめて変換
- オプションで「全音源を結合した1本の動画」も追加生成
- 変換に使った元音源は `04_Archive/実行日時/` へ自動退避
- FFmpegを自動取得して `bin/` に配置
- **日本語フォント初期同梱**（`fonts/SoukouMincho.ttf`）・Zipファイル自動解凍対応
- 日本語ファイル名テロップ対応（安全化/長さ調整あり）
- 低優先度モード、完了後フォルダ展開、スリープ
- Windows/macOS 向けの「Python未導入対応ランチャー」同梱
- 依存同期に失敗しても実行継続（GUI不可時はCLIへ自動フォールバック）
- ダブルクリック起動時に自動 `git pull --ff-only` を試行（失敗しても継続）
- **GUI に音源リスト表示・更新ボタン**（認識された音源を一覧表示）
- **処理時間推定表示**（ファイルサイズに基づく処理時間の粗い推定）

## Python 未導入PCでの実行
### Windows
1. `start.bat` をダブルクリック
2. リポジトリ更新（`git pull --ff-only`）をベストエフォートで実行
3. 初回は `uv` と Python 3.11 を `.runtime/` に自動構築
4. 依存パッケージを同期し、GUI起動（同期失敗時は利用可能構成で継続）

### macOS
1. `chmod +x start.command` を一度実行
2. `start.command` をダブルクリック（または `./start.command`）
3. リポジトリ更新（`git pull --ff-only`）をベストエフォートで実行
4. 初回は `uv` と Python 3.11 を `.runtime/` に自動構築
5. 依存パッケージを同期し、GUI起動（同期失敗時は利用可能構成で継続）

この方式により、システムPythonやグローバルモジュールに依存せず、バージョン差分問題を避けられます。

## テスト・検証
詳細な動作テスト結果は [TESTING.md](TESTING.md) をご参照ください。
- フォント自動抽出
- クリーンなインストール・起動
- 日本語ファイル名対応
- GUI 初期化連携
- アップデートメカニズム
- Flet 互換性

## 補足
- `flet` が利用できない場合は GUI 起動失敗時に自動で CLI へ切り替えます。
- `psutil` が利用できない場合でも、標準機能で低優先度化を試行します。
- テスト音源（`.wav`）は `.gitignore` にて除外されており、Github にアップロードされません。

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
