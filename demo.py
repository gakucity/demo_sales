import json
import os
import urllib.request
import streamlit as st
import google.generativeai as genai

# .env から読み込み（ローカル用。クラウドでは環境変数/Secrets を使用）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- 設定エリア ---
st.set_page_config(page_title="商談スクリプト生成", layout="centered")

# パスワード認証（APP_PASSWORD を .env / Streamlit Secrets に設定）
APP_PASSWORD = os.environ.get("APP_PASSWORD", "")
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔐 ログイン")
    pwd = st.text_input("パスワード", type="password", placeholder="パスワードを入力")
    if st.button("ログイン"):
        if not APP_PASSWORD:
            st.error("管理者が APP_PASSWORD を設定していません。.env または Streamlit の Secrets に APP_PASSWORD を追加してください。")
        elif pwd == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()

# --- 認証済み：メイン画面 ---
st.title("🏭 営業・商談スクリプト生成")
st.caption("営業が顧客と商談する際のトークスクリプトを生成します（アポ取得後の商談用）")

# APIキーは環境変数 GOOGLE_API_KEY（ローカルは .env、クラウドは Streamlit の Secrets）
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
# 3-flash を最優先、以降は枠が緩い順
MODEL_ORDER = [
    "gemini-3-flash-preview",  # 最優先（最新モデル）
    "gemini-2.5-flash-lite",   # RPD 1000
    "gemini-2.5-flash",        # RPD 250
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
]
models = {name: genai.GenerativeModel(name) for name in MODEL_ORDER}

# --- 入力画面 ---
with st.sidebar:
    st.header("基本情報")
    if st.button("🔍 利用可能なモデル一覧を取得"):
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GOOGLE_API_KEY}"
        try:
            with urllib.request.urlopen(url) as res:
                data = json.loads(res.read().decode())
            names = [m.get("name", "").replace("models/", "") for m in data.get("models", [])]
            if names:
                st.caption("このAPIキーで使えるモデル（generateContent 対応のみ）:")
                for n in sorted(names):
                    st.code(n, language=None)
            else:
                st.warning("モデルが取得できませんでした。")
        except Exception as e:
            st.error(f"取得失敗: {e}")
    st.markdown("---")
    industry = st.text_input("業界・業種", placeholder="例：製鉄、化学、水処理、食品、製紙")
    product = st.text_input("紹介する製品・ソリューション", placeholder="例：DCS、計装システム、制御盤、保全サービス")
    target_role = st.selectbox("商談相手の役職", ["担当者", "現場責任者・課長", "部門長", "経営層・役員"])

st.subheader("商談で扱う課題・ニーズ")
pain_point = st.text_area("相手の課題や検討テーマ", placeholder="例：設備老朽化による故障リスク、省人化・遠隔監視、品質の安定化、規制対応")

# --- 生成ロジック ---
if st.button("商談スクリプトを生成する", type="primary"):
    if not GOOGLE_API_KEY:
        st.error("APIキーを設定してください。")
    elif industry and product and pain_point:
        with st.spinner("商談スクリプトを執筆中..."):
            prompt = f"""
            あなたはプラント制御機器メーカーのベテラン営業です。
            {industry}のプラントオーナー（商談相手は{target_role}）に対して、
            {product}を提案する「商談用トークスクリプト」を作成してください。
            ※アポ取得後の商談（対面またはオンライン）用であり、電話のアポ取りではありません。

            【商談で扱う課題・ニーズ】: {pain_point}

            以下の構成で書いてください。特にアイスブレイクとクロージングを必ず含めること。

            1. アイスブレイク
               - 挨拶、簡単な雑談（天気・業界の話題などで場を和ませる）
               - 本日の商談の目的・進め方の共有

            2. 課題のヒアリング・共感
               - 相手の現状や課題の確認、共感の一言

            3. 製品・ソリューションの紹介とベネフィット
               - {product}の説明と、相手の課題に対するメリットを端的に

            4. 懸念・質問への対応
               - 想定される質問や懸念への切り返し例

            5. クロージング（必ず含めること）
               - 次回MTG（打ち合わせ）の日程を具体的にセットする流れ
               - 意思決定者の確認（「ご検討の際、他にどの方が関与されますか？」「決裁はどちらがお取りになりますか？」など、決裁者・意思決定者を確認する一言を忘れないこと）

            口調は丁寧で、相手のメリットを明確に伝えるスタイルにしてください。
            """
            result_text = None
            used_model = None
            for model_name in MODEL_ORDER:
                try:
                    response = models[model_name].generate_content(prompt)
                    result_text = response.text if response.text else "(空の応答)"
                    used_model = model_name
                    break
                except Exception as e:
                    # 429 または 404 なら次のモデルを試す
                    if "429" not in str(e) and "404" not in str(e):
                        st.error(f"**生成に失敗しました**\n\n`{e}`")
                        break
            if result_text is None and used_model is None:
                st.error("**利用枠に達しました**")
                st.markdown("すべてのモデルで枠超過です。しばらく（約30秒〜1分）待ってから再試行するか、[課金を有効にする](https://aistudio.google.com/)と枠が増えます。")
            if result_text:
                st.success("生成が完了しました！")
                st.caption(f"使用モデル: {used_model}")
                st.markdown("---")
                st.markdown(result_text)
    else:
        st.warning("すべての項目を入力してください。")