import json
import os
import re
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
    company_name = st.text_input("提案先企業名", placeholder="例：○○製鉄、△△化学")
    duration_minutes = st.number_input("商談時間（分）", min_value=15, max_value=120, value=60, step=5, help="スクリプトの分量をこの時間に合わせて調整します")
    st.markdown("---")
    industry = st.text_input("業界・業種", placeholder="例：製鉄、化学、水処理、食品、製紙")
    target_role = st.selectbox("商談相手の役職", ["担当者", "現場責任者・課長", "部門長", "経営層・役員"])

st.subheader("商談で扱う課題・ニーズ")
pain_point = st.text_area("相手の課題や検討テーマ", placeholder="例：設備老朽化による故障リスク、省人化・遠隔監視、品質の安定化、規制対応")

# --- サービス候補レコメンド ---
if "recommended_services" not in st.session_state:
    st.session_state.recommended_services = []

st.subheader("提案するサービス・ソリューション")
if st.session_state.recommended_services:
    st.caption("スクリプトに含めたいサービスにチェックを入れてください。")
    selected_services = []
    for i, item in enumerate(st.session_state.recommended_services):
        svc = item["name"] if isinstance(item, dict) else item
        score = item.get("score", 70) if isinstance(item, dict) else 70
        score = max(0, min(100, score))
        col_cb, col_pct, col_bar = st.columns([2, 0.8, 3])
        with col_cb:
            if st.checkbox(svc, key=f"service_cb_{i}"):
                selected_services.append(svc)
        with col_pct:
            st.write(f"**{score}%**")
        with col_bar:
            st.progress(score / 100.0)
    rec_btn = st.button("🔄 候補を再取得")
else:
    selected_services = []
    rec_btn = st.button("提案できるサービス候補を8つレコメンド", type="primary")

if rec_btn:
    if company_name and industry and pain_point:
        with st.spinner("提案先と課題からサービス候補を検討しています..."):
            rec_prompt = f"""
あなたはプラント制御機器・計装・制御ソリューションを提供するメーカーの営業です。
以下の条件から、提案できそうな製品・ソリューション・サービスを**ちょうど8つ**、具体的な名前で挙げてください。
さらに、各サービスについて「提案先企業・業界・課題との適合度」を0以上100以下の整数で付けてください。

【提案先企業】{company_name}
【業界・業種】{industry}
【相手の課題・検討テーマ】{pain_point}

回答は必ず次の形式のみにしてください。見出しや説明は不要です。
1. （サービス名）（適合度: 0-100の整数）
2. （サービス名）（適合度: 0-100の整数）
… 8つまで同様
例: 1. DCS更新・遠隔監視ソリューション（適合度: 92）
"""
            rec_text = None
            for model_name in MODEL_ORDER:
                try:
                    r = models[model_name].generate_content(rec_prompt)
                    rec_text = r.text if r.text else ""
                    break
                except Exception:
                    continue
            if rec_text:
                lines = [ln.strip() for ln in rec_text.strip().split("\n") if ln.strip()]
                parsed = []
                score_re = re.compile(r"^[1-8][\.．)\s]+(.+?)(?:\s*[（(]適合度\s*[：:]\s*(\d{1,3})[%）)%]?)?\s*$")
                trail_re = re.compile(r"^(.+?)\s*[（(]適合度\s*[：:]\s*(\d{1,3})[%）)%]?\s*$")
                for ln in lines:
                    m = score_re.match(ln)
                    if m:
                        name = m.group(1).strip()
                        score = int(m.group(2)) if m.group(2) else 70
                        score = max(0, min(100, score))
                        trail = trail_re.match(name)
                        if trail:
                            name, score = trail.group(1).strip(), max(0, min(100, int(trail.group(2))))
                        if name and not any(x["name"] == name for x in parsed):
                            parsed.append({"name": name, "score": score})
                    else:
                        m2 = re.match(r"^[1-8][\.．)\s]+(.+)$", ln)
                        if m2:
                            rest = m2.group(1).strip()
                            trail = trail_re.match(rest)
                            if trail:
                                rest, sc = trail.group(1).strip(), max(0, min(100, int(trail.group(2))))
                                if rest and not any(x["name"] == rest for x in parsed):
                                    parsed.append({"name": rest, "score": sc})
                            elif rest and not any(x["name"] == rest for x in parsed):
                                parsed.append({"name": rest, "score": 70})
                while len(parsed) < 8:
                    parsed.append({"name": f"候補{len(parsed)+1}", "score": 50})
                st.session_state.recommended_services = parsed[:8]
                st.rerun()
            else:
                st.error("サービス候補の取得に失敗しました。しばらくして再試行してください。")
    else:
        st.warning("提案先企業名・業界・課題を入力したうえで、再度ボタンを押してください。")
elif not st.session_state.recommended_services:
    st.info("👆 提案先企業名・業界・課題を入力し、「提案できるサービス候補を8つレコメンド」を押すと、AIが8つのサービス候補を表示します。")

# --- 生成ロジック ---
if st.button("商談スクリプトを生成する", type="primary", disabled=not selected_services):
    if not GOOGLE_API_KEY:
        st.error("APIキーを設定してください。")
    elif not (company_name and industry and pain_point):
        st.warning("提案先企業名・業界・課題を入力してください。")
    elif not selected_services:
        st.warning("スクリプトに含めたいサービスを1つ以上チェックしてください。")
    else:
        products_label = "、".join(selected_services)
        with st.spinner("商談スクリプトを執筆中（提案先の財務・中計・業界トレンドを反映）..."):
            prompt = f"""
            あなたはプラント制御機器メーカーのベテラン営業です。
            【提案先企業】{company_name}（{industry}、商談相手は{target_role}）に対して、
            以下の製品・ソリューションを提案する「商談用トークスクリプト」を作成してください。
            【提案するサービス】{products_label}
            ※アポ取得後の商談（対面またはオンライン）用であり、電話のアポ取りではありません。

            【重要】スクリプトの深さと分量について
            - 提案先企業（{company_name}）の財務諸表・経営指標、中期経営計画（中計）や経営方針、および{industry}業界のトレンド・課題を、あなたの知識に基づいて踏まえた「深い提案」にしてください。該当企業の情報が限られる場合は、同業種の典型的な経営課題と業界トレンドに基づいて具体的に書いてください。
            - 商談時間は **{duration_minutes}分** です。この時間内で話し切れる分量に厳密に合わせてください。{duration_minutes}分が短い場合は各セクションを簡潔に、長い場合は具体例や数字を増やすなど、実際に商談で使える長さに調整してください。

            【商談で扱う課題・ニーズ】: {pain_point}

            以下の構成で書いてください。特にアイスブレイクとクロージングを必ず含めること。
            各パートの分量配分も{duration_minutes}分に合わせて明示してください（例：アイスブレイク〜3分、本論〜20分、クロージング〜5分）。

            1. アイスブレイク
               - 挨拶、簡単な雑談（業界の話題や相手企業に触れつつ場を和ませる）
               - 本日の商談の目的・進め方の共有

            2. 課題のヒアリング・共感
               - 相手の現状や課題の確認、共感の一言
               - （可能なら）相手企業の経営方針・中計や業界トレンドに触れつつ、課題を深掘りする問いかけ

            3. 製品・ソリューションの紹介とベネフィット
               - 選択した各サービス（{products_label}）について、相手の課題・経営目標に対するメリットを端的に説明する
               - 財務的・経営的な効果（コスト削減、リスク低減、収益貢献など）に触れると説得力が増します

            4. 懸念・質問への対応
               - 想定される質問や懸念への切り返し例

            5. クロージング（必ず含めること）
               - 次回MTG（打ち合わせ）の日程を具体的にセットする流れ
               - 意思決定者の確認（「ご検討の際、他にどの方が関与されますか？」「決裁はどちらがお取りになりますか？」など、決裁者・意思決定者を確認する一言を忘れないこと）

            口調は丁寧で、相手のメリットを明確に伝えるスタイルにしてください。スクリプト全体の文字量・話す分量は{duration_minutes}分で収まるようにしてください。
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