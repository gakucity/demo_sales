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
st.set_page_config(page_title="AI営業トーク生成くん", layout="centered")
st.title("🎙️ AI営業トークスクリプト生成")

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
    industry = st.text_input("相手の業界", placeholder="例：飲食チェーン")
    product = st.text_input("紹介する商材", placeholder="例：無人レジシステム")
    target_role = st.selectbox("相手の役職", ["担当者", "店長・現場責任者", "経営層・役員"])

st.subheader("どんな課題を解決しますか？")
pain_point = st.text_area("解決したい悩み", placeholder="例：人手不足でレジ待ちが発生し、客を取りこぼしている")

# --- 生成ロジック ---
if st.button("トークスクリプトを生成する", type="primary"):
    if not GOOGLE_API_KEY:
        st.error("APIキーを設定してください。")
    elif industry and product and pain_point:
        with st.spinner("プロ営業マンが執筆中..."):
            prompt = f"""
            あなたはトップセールスです。{industry}の{target_role}に対して、
            {product}を提案するための「テレアポ用トークスクリプト」を作成してください。
            
            【解決する悩み】: {pain_point}
            
            構成案：
            1. 受付突破の第一声
            2. 本人（{target_role}）へのフロントトーク
            3. 課題への共感と「ベネフィット」の提示
            4. 懸念点（「忙しい」「間に合ってる」）への切り返し
            5. 具体的な日程調整（クロージング）
            
            口調は丁寧ながらも、相手のメリットを端的に伝えるスタイルでお願いします。
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