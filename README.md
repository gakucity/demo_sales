# demo_sales

AI営業トークスクリプト生成アプリ（Streamlit + Google Gemini）

## ローカルで動かす

1. 依存関係: `pip install -r requirements.txt`
2. `.env` に `GOOGLE_API_KEY=あなたのキー` を設定
3. 起動: `streamlit run demo.py`

## クラウドデプロイ手順（Streamlit Community Cloud）

1. このリポジトリを GitHub にプッシュする（まだなら `git init` → `git add .` → `git commit` → `git remote add origin ...` → `git push`）
2. [Streamlit Community Cloud](https://share.streamlit.io/) にアクセスし、**Sign in with GitHub** でログイン
3. **New app** をクリック
4. **Repository** で `あなたのユーザー名/demo_sales`、**Branch** で `main`、**Main file path** で `demo.py` を選択して **Deploy!**
5. デプロイ画面の **Advanced settings** を開き、**Secrets** に次を追加:
   ```
   GOOGLE_API_KEY=あなたのGoogle APIキー
   ```
6. 保存すると自動で再デプロイされ、数分でアプリのURLが発行されます（例: `https://xxx.streamlit.app`）
