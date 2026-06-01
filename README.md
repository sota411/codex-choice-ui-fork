# Codex CLI 自分用改造版

OpenAI Codex CLI の `request_user_input` を、自分用に調整した fork です。

## 変更点

- Plan Mode の選択UIは、既定で `4択 + Custom answer` を表示します。
- 通常選択肢の数は config で変更できます。
- 1回の選択UIで出せる質問数の上限も config で変更できます。
- モデル側に `isOther` を書かせず、クライアント側で自由記述欄を自動追加します。
- 設定した選択肢数・質問数上限に合わない tool 呼び出しは失敗させます。

## セットアップ

Rust と開発用コマンドを入れます。

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
```

```bash
source "$HOME/.cargo/env"
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

リポジトリを取得してビルドします。

```bash
git clone https://github.com/sota411/codex-choice-ui-fork.git
```

```bash
cd codex-choice-ui-fork/codex-rs
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

`codex-custom` が見つからない場合は、`$HOME/.local/bin` を `PATH` に追加してください。

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## 使い方

Plan Mode で質問が必要になると、既定では通常選択肢4個と `Custom answer` が表示されます。

```text
/plan 実装方針を確認しながら計画して。
```

選択肢数を変える場合は、`~/.codex/config.toml` に設定します。

```toml
[tools.experimental_request_user_input]
default_options_count = 5
max_questions = 4
```

この例では、1回の選択UIで最大4問まで出せて、各質問は `5択 + Custom answer` になります。`default_options_count = 0` と `max_questions = 0` は無効です。設定変更後は Codex を再起動してください。

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
