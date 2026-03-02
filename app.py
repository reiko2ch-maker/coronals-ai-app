import os
import re
import time
import sqlite3
import google.generativeai as genai
from datetime import datetime
import streamlit as st

# --- UIカスタマイズ設定 ---
st.set_page_config(page_title="AI自動コンテンツ錬成システム", layout="centered", page_icon="✨")

# --- セッション状態の初期化 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'login_time' not in st.session_state:
    st.session_state.login_time = 0
if 'preview_product' not in st.session_state:
    st.session_state.preview_product = False
if 'preview_manual' not in st.session_state:
    st.session_state.preview_manual = False
if 'display_product' not in st.session_state:
    st.session_state.display_product = None
if 'display_manual' not in st.session_state:
    st.session_state.display_manual = None
if 'display_keyword' not in st.session_state:
    st.session_state.display_keyword = None

# --- CSS切り替え（プレビュー or 通常） ---
if st.session_state.preview_product or st.session_state.preview_manual:
    st.markdown("""
<style>
/* 印刷プレビュー用CSS（UI消去・白背景・黒文字フォーカス） */
.stApp {
    background: #ffffff !important;
}
[data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"] {
    display: none !important;
}
/* コンテナの高さ制限やスクロールを完全に解除して全内容を描画させる（複数ページPDF対応の要点） */
.block-container, .stApp, .main, div.stMarkdown, div.stVerticalBlock {
    padding: 0 !important;
    margin: 0 auto !important;
    max-width: 800px !important;
    height: auto !important;
    overflow: visible !important;
}
/* すべてのテキスト要素を強制的に黒無地に */
h1, h2, h3, h4, h5, h6, p, div, span, li, ul, ol, strong, em, b, i {
    background: none !important;
    -webkit-background-clip: unset !important;
    -webkit-text-fill-color: #000000 !important;
    color: #000000 !important;
    text-shadow: none !important;
}
.card {
    background: transparent !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    border: none !important;
    box-shadow: none !important;
    padding: 1rem 1.5rem !important;
    margin: 0 !important;
    overflow: visible !important;
    height: auto !important;
}
hr {
    border-color: #dddddd !important;
    margin: 2rem 0 !important;
}
/* 戻るボタンのスタイル */
div.stButton > button {
    background: #f0f0f0 !important;
    color: #333333 !important;
    border: 1px solid #cccccc !important;
    box-shadow: none !important;
    padding: 0.6rem 1.2rem !important;
    border-radius: 8px !important;
    width: 100% !important;
    font-size: 1.1rem !important;
    margin-bottom: 1rem !important;
    margin-top: 1rem !important;
}
/* ---------- Safari 印刷（Print）時の最適化CSS ---------- */
@media print {
    @page { margin: 0; }
    body { padding: 10mm; }
    /* ボタンや不要なUIは印刷版から完全に消す */
    div.stButton, .stAlert { display: none !important; }
    /* 余白やスクロール制限をリセットして最初から最後まで出力されるように */
    .block-container, .stApp, .main, div.stMarkdown, div.stVerticalBlock, .card {
        padding-top: 0 !important;
        height: auto !important;
        overflow: visible !important;
        position: static !important;
    }
    /* 改ページ制御（見出しの直後や段落の途中で切れないように） */
    h2, h3 { page-break-after: avoid; margin-top: 1.5rem !important; }
    p, li { orphans: 3; widows: 3; }
    /* 区切り線（hr）の前で改ページを促す */
    hr { page-break-before: always; border: none; height: 1px; }
}
</style>
""", unsafe_allow_html=True)
else:
    st.markdown("""
<style>
/* --- 通常画面：ハイテクSaaSデザイン --- */
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #000000 100%);
    color: #ffffff;
}
.block-container {
    padding-top: 3rem;
    padding-bottom: 5rem;
    max-width: 850px;
}
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
.stTextInput label p, .stPasswordInput label p {
    color: #ffffff !important;
    font-weight: bold !important;
    font-size: 1.1rem !important;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
}
div[data-baseweb="input"] {
    background-color: rgba(0, 0, 0, 0.2) !important;
    border-radius: 8px !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
}
div[data-baseweb="input"] input {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-weight: 500 !important;
    caret-color: #ffffff !important;
}
div[data-baseweb="input"] input::placeholder {
    color: #aaaaaa !important;
    -webkit-text-fill-color: #aaaaaa !important;
}
b, strong {
    color: #f1c40f !important; /* 強調を少し金色に */
}
/* 錬成ボタンの装飾 */
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
    box-shadow: 0 0 25px rgba(142, 84, 233, 0.8) !important;
}
/* コンテンツエリア用（マークダウンを綺麗に見せる） */
.css-1n76uvr { line-height: 1.8; }
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

# --- HTMLファイル出力機能 ---
def create_html(title, text):
    html_content = text.replace('\n', '<br>')
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Helvetica Neue', Arial, 'Hiragino Kaku Gothic ProN', 'Hiragino Sans', Meiryo, sans-serif;
            padding: 20px;
            line-height: 1.8;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            background-color: #fcfcfc;
        }}
        h1, h2, h3 {{ color: #1a1a1a; border-bottom: 2px solid #eaeaea; padding-bottom: 8px; margin-top: 24px; }}
        .container {{ background: #ffffff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }}
        @media print {{
            body, .container {{ background-color: transparent !important; box-shadow: none !important; padding: 0 !important; margin: 0 !important; color: #000000 !important; }}
        }}
    </style>
</head>
<body>
    <div class="container">{html_content}</div>
</body>
</html>"""
    return html.encode('utf-8')


# ログイン状態の確認（1時間有効、3600秒）
current_time = time.time()
if st.session_state.logged_in and (current_time - st.session_state.login_time > 3600):
    st.session_state.logged_in = False
    st.session_state.login_time = 0
    st.session_state.preview_product = False
    st.session_state.preview_manual = False
    st.warning("セッションがタイムアウトしました。再度ログインしてください。")

# ------------------------------------------------
# アプリケーション UI (ルート分岐)
# ------------------------------------------------
if not st.session_state.logged_in:
    # ログイン画面
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

elif st.session_state.preview_product:
    # 商品ページ専用プレビュー
    if st.button("← 編集画面に戻る"):
        st.session_state.preview_product = False
        st.rerun()
        
    st.info("💡 Safariの方は、下部の「共有ボタン」→「プリント」を押すと、綺麗なPDFとして保存できます。")
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"<h2>【商品ページ】{st.session_state.display_keyword}</h2>", unsafe_allow_html=True)
    st.markdown(st.session_state.display_product)
    st.markdown('</div>', unsafe_allow_html=True)

elif st.session_state.preview_manual:
    # マニュアル専用プレビュー
    if st.button("← 編集画面に戻る"):
        st.session_state.preview_manual = False
        st.rerun()
        
    st.info("💡 Safariの方は、下部の「共有ボタン」→「プリント」を押すと、綺麗なPDFとして保存できます。")
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"<h2>【マニュアル】{st.session_state.display_keyword}</h2>", unsafe_allow_html=True)
    st.markdown(st.session_state.display_manual)
    st.markdown('</div>', unsafe_allow_html=True)

else:
    # ------------------------------------------------
    # 通常のメイン画面（編集・生成用）
    # ------------------------------------------------
    st.sidebar.title("📚 過去の錬成履歴")
    history_records = load_history()
    
    selected_record_id = None
    if history_records:
        for record_id, timestamp, kw in history_records:
            if st.sidebar.button(f"✨ {kw}\n({timestamp})", key=f"hist_{record_id}"):
                selected_record_id = record_id
    else:
        st.sidebar.info("履歴はまだありません。")

    st.markdown("<h1>AI自動コンテンツ錬成システム</h1>", unsafe_allow_html=True)
    
    # 使い方ガイド（メイン画面トップに常設）
    with st.expander("📘 システムの使い方（履歴の活用）"):
        st.markdown("""
        - 錬成した「商品ページ」や「マニュアル」は、左上の**「過去の錬成履歴」に自動で保存**されます。
        - 履歴のボタンを押せば、いつ開いても同じ内容を一瞬で復元可能です。間違って画面を閉じても安心です。
        """)
    with st.expander("📱 スマホでのPDF保存方法（Safari推奨）"):
        st.markdown("""
        **【iPhone/Safariの場合】**
        1. 錬成完了後、上部の**「📱 プレビューを表示」**ボタンを押す
        2. 白背景の専用画面になったら、画面下部の **共有（□から↑矢印が出ているアイコン）** をタップ
        3. メニューを下へスクロールし **「プリント」** をタップ
        4. オプション画面が開くので、右上の **「プリント」 または プレビュー画像を二本指で拡大（ピンチアウト）** する
        5. さらに共有ボタンを押して **「ファイルに保存」** などを選べば、美しい複数ページPDFとして保存完了！
        """)

    if selected_record_id:
        row = load_generation(selected_record_id)
        if row:
            st.session_state.display_product, st.session_state.display_manual = row
            st.session_state.display_keyword = next((rec[2] for rec in history_records if rec[0] == selected_record_id), "不明")
            st.info(f"履歴を復元しました: 『{st.session_state.display_keyword}』")

    # 結果がある場合、最上部（入力フォームの上）にプレビュー・保存ボタンを大々的に表示
    if st.session_state.display_product and st.session_state.display_manual:
        st.markdown("---")
        st.markdown("<h3 style='text-align:center;'>📱 プリント保存用プレビュー</h3>", unsafe_allow_html=True)
        colA, colB = st.columns(2)
        with colA:
            if st.button("📄 商品ページを表示\n(保存用)", key="btn_top_preview_prod"):
                st.session_state.preview_product = True
                st.rerun()
        with colB:
            if st.button("📗 マニュアルを表示\n(保存用)", key="btn_top_preview_manu"):
                st.session_state.preview_manual = True
                st.rerun()
        st.markdown("---")

    # 入力フォーム
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
                    genai.configure(api_key=api_key)

                    model = genai.GenerativeModel('gemini-2.5-flash', safety_settings={
                        'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                        'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                        'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                        'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
                    })

                    research_prompt = f"ココナラで「{genre_keyword}」の売れ筋を分析し、ターゲットの悩みと解決策をまとめてください。"
                    research_data = model.generate_content(research_prompt).text

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

                    manual_prompt = f"以下の商品内容に沿った、購入者が満足する実践的なノウハウマニュアルをMarkdown形式で詳しく執筆してください。\n\n商品内容:\n{product_package}"
                    manual_content = model.generate_content(manual_prompt).text
                    
                    save_to_db(genre_keyword, product_package, manual_content)

                    # 表示変数にセット
                    st.session_state.display_product = product_package
                    st.session_state.display_manual = manual_content
                    st.session_state.display_keyword = genre_keyword

                    st.success("✅ 錬成が完了し、履歴に保存されました！上のプレビューボタンから結果を確認できます。")
                    
                    time.sleep(1)
                    st.rerun()

                except Exception as e:
                    st.error(f"エラーが発生しました: 今回入力したAPIキーが正しいか、ネットワーク状況をご確認ください。\n({str(e)})")

    # 結果のプレビューカード（通常画面の下部にも念のため表示）
    if st.session_state.display_product and st.session_state.display_manual and st.session_state.display_keyword:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## 📄 商品ページ")
        st.markdown(st.session_state.display_product)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("## 📗 マニュアル")
        st.markdown(st.session_state.display_manual)
        st.markdown('</div>', unsafe_allow_html=True)

        # ファイル名用のサニタイズ
        sanitized_genre = re.sub(r'[\\/:*?"<>| ]', '_', st.session_state.display_keyword)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### 💾 ダウンロード（PC・代替用）")
        
        product_html_bytes = create_html(f"【出品ページ】{st.session_state.display_keyword}", st.session_state.display_product)
        manual_html_bytes = create_html(f"【マニュアル】{st.session_state.display_keyword}", st.session_state.display_manual)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("<div style='text-align: center; margin-bottom: 10px;'><b>💻 PC向け (Markdown)</b></div>", unsafe_allow_html=True)
            st.download_button(
                label="🛒 商品 [.md]",
                data=st.session_state.display_product,
                file_name=f"{sanitized_genre}_product_page_{timestamp}.md",
                mime="text/markdown",
                use_container_width=True
            )
            st.download_button(
                label="📘 マニ [.md]",
                data=st.session_state.display_manual,
                file_name=f"{sanitized_genre}_manual_{timestamp}.md",
                mime="text/markdown",
                use_container_width=True
            )
            
        with col2:
            st.markdown("<div style='text-align: center; margin-bottom: 10px;'><b>📱 HTMLによる保存</b></div>", unsafe_allow_html=True)
            st.download_button(
                label="🌐 商品 [.html]",
                data=product_html_bytes,
                file_name=f"{sanitized_genre}_product_page_{timestamp}.html",
                mime="text/html",
                use_container_width=True
            )
            st.download_button(
                label="🌐 マニ [.html]",
                data=manual_html_bytes,
                file_name=f"{sanitized_genre}_manual_{timestamp}.html",
                mime="text/html",
                use_container_width=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
