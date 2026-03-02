import os
import re
import time
import sqlite3
import requests
import google.generativeai as genai
from datetime import datetime
import streamlit as st
from fpdf import FPDF

# --- UIカスタマイズ設定 ---
st.set_page_config(page_title="AI自動コンテンツ錬成システム", layout="centered", page_icon="✨")

st.markdown("""
<style>
/* アプリ全体の背景（ダークネイビー・サイバー・ハイテク感） */
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #000000 100%);
    color: #ffffff;
}

/* メインコンテナの余白調整 */
.block-container {
    padding-top: 3rem;
    padding-bottom: 5rem;
    max-width: 850px;
}

/* 見出しの豪華な装飾（発光感のある水色/Cyan） */
h1 {
    background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800 !important;
    text-align: center;
    margin-bottom: 2rem !important;
    text-shadow: 0 0 10px rgba(0, 242, 254, 0.4);
}

h2, h3 {
    color: #00f2fe !important;
    text-shadow: 0 0 8px rgba(0, 242, 254, 0.3);
}

/* カード型UIの定義・グラスモーフィズム（Glassmorphism）パネル */
.card {
    background: rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 16px;
    padding: 2.5rem;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    margin-bottom: 2rem;
    color: #ffffff;
}

/* --- 入力欄上の文字（ラベル）を絶対に表示させる --- */
.stTextInput label p, .stPasswordInput label p {
    color: #ffffff !important;
    font-weight: bold !important;
    font-size: 1.1rem !important;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
}

/* --- 入力欄とボタンの高級感アップ（Streamlitのデフォルト入力を強制上書き） --- */
div[data-baseweb="input"] {
    background-color: rgba(0, 0, 0, 0.2) !important; /* 少し暗い半透明 */
    border-radius: 8px !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
}

div[data-baseweb="input"] input {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important; /* ←文字化け/透明化を防ぐ特効薬 */
    font-weight: 500 !important;
    caret-color: #ffffff !important; /* カーソルの色も白に */
}

div[data-baseweb="input"] input::placeholder {
    color: #aaaaaa !important;
    -webkit-text-fill-color: #aaaaaa !important;
}

/* 錬成ボタンの装飾（パープルグラデーション・ホバー発光） */
div.stButton > button {
    background: linear-gradient(135deg, #4776E6 0%, #8E54E9 100%) !important;
    color: white !important;
    border: none !important;
    padding: 0.8rem 2.5rem !important;
    border-radius: 50px !important;
    font-size: 1.15rem !important;
    font-weight: bold !important;
    box-shadow: 0 0 15px rgba(142, 84, 233, 0.5) !important;
    transition: all 0.3s ease !important;
    width: 100%;
}
div.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 0 25px rgba(142, 84, 233, 0.8) !important; /* glow効果 */
}
</style>
""", unsafe_allow_html=True)

# --- DB初期化 ---
DB_PATH = "history.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS generations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            genre_keyword TEXT,
            product_text TEXT,
            manual_text TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_to_db(genre_keyword, product_text, manual_text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    c.execute('INSERT INTO generations (timestamp, genre_keyword, product_text, manual_text) VALUES (?, ?, ?, ?)',
              (timestamp, genre_keyword, product_text, manual_text))
    conn.commit()
    conn.close()

def load_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, timestamp, genre_keyword FROM generations ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    return rows

def load_generation(gen_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT product_text, manual_text FROM generations WHERE id = ?', (gen_id,))
    row = c.fetchone()
    conn.close()
    return row

init_db()

# --- PDF生成機能 ---
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP-Regular.ttf"
FONT_PATH = "NotoSansJP-Regular.ttf"

def download_font():
    if not os.path.exists(FONT_PATH):
        try:
            response = requests.get(FONT_URL)
            response.raise_for_status()
            with open(FONT_PATH, "wb") as f:
                f.write(response.content)
        except Exception as e:
            st.error(f"フォントのダウンロードに失敗しました: {e}")

def create_pdf(text):
    download_font()
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists(FONT_PATH):
        pdf.add_font("NotoSansJP", style="", fname=FONT_PATH, uni=True)
        pdf.set_font("NotoSansJP", size=11)
    else:
        pdf.set_font("Helvetica", size=11)
    
    # PDFにテキストを出力
    pdf.multi_cell(0, 8, txt=text)
    
    try:
        pdf_bytes = pdf.output()
        if isinstance(pdf_bytes, str):
            pdf_bytes = pdf_bytes.encode('latin-1')
        return bytes(pdf_bytes)
    except Exception:
        # 古いfpdfの場合は dest='S'
        return pdf.output(dest='S').encode('latin-1')


# --- セッション状態の初期化 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'login_time' not in st.session_state:
    st.session_state.login_time = 0

# ログイン状態の確認（1時間有効、3600秒）
current_time = time.time()
if st.session_state.logged_in and (current_time - st.session_state.login_time > 3600):
    st.session_state.logged_in = False
    st.session_state.login_time = 0
    st.warning("セッションがタイムアウトしました。再度ログインしてください。")

# --- アプリケーションUI ---
if not st.session_state.logged_in:
    st.markdown("<h1>System Login</h1>", unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    password = st.text_input("システムパスワード", type="password", placeholder="パスワードを入力")
    if st.button("ログイン"):
        if password == "coconala2026":
            st.session_state.logged_in = True
            st.session_state.login_time = time.time()
            st.rerun()
        else:
            st.error("パスワードが間違っています。")
    st.markdown('</div>', unsafe_allow_html=True)
else:
    # --- サイドバー（履歴表示） ---
    st.sidebar.title("📚 過去の錬成履歴")
    history_records = load_history()
    
    selected_record_id = None
    if history_records:
        for record_id, timestamp, kw in history_records:
            if st.sidebar.button(f"✨ {kw}\n({timestamp})", key=f"hist_{record_id}"):
                selected_record_id = record_id
    else:
        st.sidebar.info("履歴はまだありません。")

    # --- メイン画面 ---
    st.markdown("<h1>AI自動コンテンツ錬成システム</h1>", unsafe_allow_html=True)
    
    # データ表示用変数
    display_product = None
    display_manual = None
    display_keyword = None

    if selected_record_id:
        row = load_generation(selected_record_id)
        if row:
            display_product, display_manual = row
            display_keyword = next((rec[2] for rec in history_records if rec[0] == selected_record_id), "不明")
            st.info(f"履歴を復元しました: 『{display_keyword}』")

    # 入力フォーム（常に上部に表示）
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🔑 APIキー設定")
    api_key = st.text_input("ご自身のGemini APIキーを入力してください", type="password", placeholder="AIzaSy...")
    
    st.markdown("### 🎯 錬成ターゲット")
    genre_keyword = st.text_input("リサーチ・作成したいジャンルを入力してください:", placeholder="例：SNS集客、占い、動画編集...")
    
    generate_clicked = st.button("錬成スタート")
    st.markdown('</div>', unsafe_allow_html=True)

    if generate_clicked:
        if not api_key:
            st.warning("⚠️ 錬成を開始するにはAPIキーが必要です")
        elif not genre_keyword:
            st.warning("⚠️ ジャンルを入力してください。")
        else:
            with st.spinner("錬成中...AIが市場を分析し、コンテンツを生成しています..."):
                try:
                    # ユーザーが入力したAPIキーを使用
                    genai.configure(api_key=api_key)

                    model = genai.GenerativeModel('gemini-2.5-flash', safety_settings={
                        'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                        'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                        'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                        'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
                    })

                    # Step 1: 市場分析
                    research_prompt = f"ココナラで「{genre_keyword}」の売れ筋を分析し、ターゲットの悩みと解決策をまとめてください。"
                    research_data = model.generate_content(research_prompt).text

                    # Step 2: 出品ページ・プロンプト生成
                    package_prompt = f"""以下の分析をもとに、ココナラでの「出品ページ用テキスト」と「サムネイル生成プロンプト」を作成してください。
必ず以下の構成と条件（景品表示法・プラットフォームガイドライン遵守）を厳守して出力してください。

【出力要件・禁止事項】
- 断定的表現（絶対、必ず、100%稼げる 等）は一切使用せず、「効率化を支援」「再現性を重視した設計」等の安全な表現を使用すること。
- 根拠なき最上級表現（日本一、最高峰 等）を禁止すること。

【出力構成順序】
1. 商品タイトル（キャッチーかつ安全な表現）
2. 商品説明文（1000文字以内）
   ※必ず説明文の末尾に以下の免責事項をそのまま挿入すること。
   「※本サービスは利益を保証するものではなく、学習や実践のサポートを目的としています」
3. 購入にあたってのお願い（1000文字以内）
4. よくある質問（FAQ）厳選3選
5. サムネイル作成用AIプロンプト
   ※nanoBANANA2等の画像生成AI用。アスペクト比 1220x1240 に適した高品質な英語プロンプトを記述。
6. 画像イメージの日本語解説

分析データ:
{research_data}
"""
                    product_package = model.generate_content(package_prompt).text

                    # Step 3: マニュアル生成
                    manual_prompt = f"以下の商品内容に沿った、購入者が満足する実践的なノウハウマニュアルをMarkdown形式で詳しく執筆してください。\n\n商品内容:\n{product_package}"
                    manual_content = model.generate_content(manual_prompt).text
                    
                    # データベースに保存
                    save_to_db(genre_keyword, product_package, manual_content)

                    # 表示変数にセット
                    display_product = product_package
                    display_manual = manual_content
                    display_keyword = genre_keyword

                    st.success("✅ 錬成が完了し、履歴に保存されました！")
                    
                    # 保存後に再度履歴を反映して表示するためにリロード
                    time.sleep(1)
                    st.rerun()

                except Exception as e:
                    st.error(f"エラーが発生しました: 今回入力したAPIキーが正しいか、ネットワーク状況をご確認ください。\n({str(e)})")

    # 結果のプレビューとダウンロード
    if display_product and display_manual and display_keyword:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## 📄 商品ページ")
        st.markdown(display_product)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## 📗 マニュアル")
        st.markdown(display_manual)
        st.markdown('</div>', unsafe_allow_html=True)

        # ファイル名用のサニタイズ
        sanitized_genre = re.sub(r'[\\/:*?"<>| ]', '_', display_keyword)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 💾 ファイルのダウンロード")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**PC・Markdown向け**")
            st.download_button(
                label="🛒 商品ページ (.md)",
                data=display_product,
                file_name=f"{sanitized_genre}_product_page_{timestamp}.md",
                mime="text/markdown",
                use_container_width=True
            )
            st.download_button(
                label="📘 マニュアル (.md)",
                data=display_manual,
                file_name=f"{sanitized_genre}_manual_{timestamp}.md",
                mime="text/markdown",
                use_container_width=True
            )
            
        with col2:
            st.markdown("**スマホ・PDF向け**")
            
            with st.spinner("PDFデータ作成中..."):
                try:
                    product_pdf_bytes = create_pdf(display_product)
                    st.download_button(
                        label="📄 商品ページ (.pdf)",
                        data=product_pdf_bytes,
                        file_name=f"{sanitized_genre}_product_page_{timestamp}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"商品ページのPDF化に失敗しました: {e}")
                
            with st.spinner("PDFデータ作成中..."):
                try:
                    manual_pdf_bytes = create_pdf(display_manual)
                    st.download_button(
                        label="📄 マニュアル (.pdf)",
                        data=manual_pdf_bytes,
                        file_name=f"{sanitized_genre}_manual_{timestamp}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"マニュアルのPDF化に失敗しました: {e}")
        
        st.markdown('</div>', unsafe_allow_html=True)
