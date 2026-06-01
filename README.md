# Codex CLI 自分用改造版

OpenAI Codex CLI を自分用に調整した fork です。

## 何が変わったか

- `request_user_input` の選択肢に `Other` を常時追加しない。
- 自由記入が必要な質問だけ `isOther: true` で `Custom answer` を表示する。
- Plan Mode では `request_user_input` を 2-6 択で使う。
- 7択以上が必要な場合は、無理に選択UIへ詰めず通常チャットで番号付きリストにする。

## セットアップ

Rust が未導入の場合:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
```

```bash
source "$HOME/.cargo/env"
```

リポジトリを取得してビルドします。

```bash
git clone https://github.com/sota411/codex-choice-ui-fork.git
```

```bash
cd codex-choice-ui-fork/codex-rs
```

```bash
rustup component add rustfmt
```

```bash
rustup component add clippy
```

```bash
cargo install --locked just
```

```bash
cargo install --locked cargo-nextest
```

```bash
cargo build --bin codex
```

## 起動方法

リポジトリ内で直接起動する場合:

```bash
./target/debug/codex
```

通常の `codex` と分けて使う場合:

```bash
mkdir -p "$HOME/.local/bin"
```

```bash
ln -sf "$PWD/target/debug/codex" "$HOME/.local/bin/codex-custom"
```

```bash
codex-custom
```

バージョン確認:

```bash
codex-custom --version
```

`codex-custom` が見つからない場合は、`$HOME/.local/bin` を `PATH` に追加してください。

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## 使い方

Plan Mode で選択肢UIを出したいときは、質問文で選択肢数を指定します。

```text
/plan 実装方針を4択で質問して。自由記入は不要。
```

自由記入も出したい場合:

```text
/plan 実装方針を3択で質問して。自由記入も必要なので isOther を true にして。
```

期待する表示:

- 自由記入なし: 指定した選択肢だけが表示される。
- 自由記入あり: 通常選択肢に加えて `Custom answer` が表示される。

## 選択肢数の変え方

使うだけなら、プロンプトで `3択`、`4択`、`6択` のように指定します。

既定の方針をコード側で変える場合は、主に次を編集します。

- `codex-rs/collaboration-mode-templates/templates/plan.md`
  - Plan Mode が何択を推奨するかを変える。
- `codex-rs/core/src/tools/handlers/request_user_input_spec.rs`
  - `request_user_input` tool の説明や schema を変える。
- `codex-rs/tui/src/bottom_pane/request_user_input/mod.rs`
  - TUI上の `Custom answer` 表示を変える。

## 動作確認

```bash
just test -p codex-core request_user_input
```

```bash
just test -p codex-tui request_user_input
```

```bash
cargo build --bin codex
```

## ライセンス

元リポジトリと同じく Apache-2.0 License です。
