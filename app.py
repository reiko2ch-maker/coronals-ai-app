import re
import google.generativeai as genai
from datetime import datetime
import streamlit as st

# セッション状態の初期化
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# 第一のロック：システムパスワード
if not st.session_state.logged_in:
    st.title("システムログイン")
    password = st.text_input("システムパスワードを入力してください", type="password")
    if st.button("ログイン"):
        if password == "coconala2026":
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("パスワードが間違っています。")
else:
    # メインシステム（第二のロック含む）
    st.title("AI自動コンテンツ錬成システム")
    
    # 第二のロック：Gemini APIキーの入力
    api_key = st.text_input("ご自身のGemini APIキーを入力してください", type="password")
    
    # ジャンル入力
    genre_keyword = st.text_input("リサーチ・作成したいジャンルを入力してください:")

    # 生成ボタン
    if st.button("錬成スタート"):
        if not api_key:
            st.warning("⚠️ 錬成を開始するにはAPIキーが必要です")
        elif not genre_keyword:
            st.warning("ジャンルを入力してください。")
        else:
            with st.spinner("錬成中...AIが市場を分析し、コンテンツを生成しています..."):
                try:
                    # ユーザーが入力したAPIキーを使用
                    genai.configure(api_key=api_key)

                    # 現在一番安定している最新のPro/Flashモデルに修正し、セーフティ設定を緩和します
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

                    # プレビュー表示
                    st.success("✅ 錬成が完了しました！")
                    
                    st.markdown("## 📄 商品ページ プレビュー")
                    st.markdown(product_package)
                    
                    st.markdown("## 📗 マニュアル プレビュー")
                    st.markdown(manual_content)

                    # ダウンロード用ファイル名の生成
                    sanitized_genre = re.sub(r'[\\/:*?"<>| ]', '_', genre_keyword)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    product_filename = f"{sanitized_genre}_product_page_{timestamp}.md"
                    manual_filename = f"{sanitized_genre}_manual_content_{timestamp}.md"

                    # ダウンロードボタンの配置
                    st.markdown("### 💾 ファイルのダウンロード")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.download_button(
                            label="🛒 商品ページを保存",
                            data=product_package,
                            file_name=product_filename,
                            mime="text/markdown"
                        )
                    
                    with col2:
                        st.download_button(
                            label="📘 マニュアルを保存",
                            data=manual_content,
                            file_name=manual_filename,
                            mime="text/markdown"
                        )

                except Exception as e:
                    st.error(f"エラーが発生しました: 今回入力したAPIキーが正しいかご確認ください。\n({str(e)})")
