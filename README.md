# demo_sales

プラント制御機器メーカーがプラントオーナーに営業する際の**商談用トークスクリプト**を生成するアプリ（Streamlit + Google Gemini）。アイスブレイクからクロージング（次回MTGのセット・意思決定者の確認）までをカバーします。

## ローカルで動かす

1. 依存関係: `pip install -r requirements.txt`
2. `.env` に次を設定:
   - `GOOGLE_API_KEY=あなたのキー`
   - `APP_PASSWORD=ログイン用パスワード`（知っている人だけがアプリを使えるようにする）
3. 起動: `streamlit run demo.py`

## クラウドデプロイ手順（Streamlit Community Cloud）

1. このリポジトリを GitHub にプッシュする（まだなら `git init` → `git add .` → `git commit` → `git remote add origin ...` → `git push`）
2. [Streamlit Community Cloud](https://share.streamlit.io/) にアクセスし、**Sign in with GitHub** でログイン
3. **New app** をクリック
4. **Repository** で `あなたのユーザー名/demo_sales`、**Branch** で `main`、**Main file path** で `demo.py` を選択して **Deploy!**
5. デプロイ画面の **Advanced settings** を開き、**Secrets** に次を追加:
   ```
   GOOGLE_API_KEY=あなたのGoogle APIキー
   APP_PASSWORD=ログイン用パスワード
   ```
6. 保存すると自動で再デプロイされ、数分でアプリのURLが発行されます（例: `https://xxx.streamlit.app`）
