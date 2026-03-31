import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

# ページの設定
st.set_page_config(page_title="楽天レビュー完全収集ツール", page_icon="📊")

st.title("📊 楽天レビュー完全収集ツール")
st.write("楽天の「商品ページURL」または「レビュー一覧ページURL」を入力してください。全件一括収集します！")

# Step 1: URLを入力する枠
input_url = st.text_input("ここにURLを貼り付けてください", placeholder="https://item.rakuten.co.jp/... または https://review.rakuten.co.jp/...")

# ボタンを押した時の動き
if st.button("データ収集開始"):
    if not input_url:
        st.warning("⚠️ URLが入力されていません！")
    else:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
        }

        try:
            review_url_base = None

            # ==========================================
            # ルートA：最初から「レビュー専用URL」が入力された場合（直行ルート！）
            # ==========================================
            if "review.rakuten.co.jp/item/1/" in input_url:
                match = re.search(r'(https://review\.rakuten\.co\.jp/item/1/\d+_\d+)', input_url)
                if match:
                    review_url_base = match.group(1)
                    st.success("✅ レビュー専用URLを検知しました！直接データの収集を開始します。")
                else:
                    st.error("❌ レビューURLの形式が正しくありません。")
                    st.stop()

            # ==========================================
            # ルートB：「商品ページURL」が入力された場合（探索ルート）
            # ==========================================
            else:
                with st.spinner("商品ページからレビューリンクを探索中..."):
                    res = requests.get(input_url, headers=headers)
                    html_text = res.text
                    
                    # どんな形でもいいから review.rakuten.co.jp のリンクを強制的に引っこ抜く最強の正規表現
                    match = re.search(r'(https://review\.rakuten\.co\.jp/item/1/\d+_\d+)', html_text)
                    
                    if match:
                        review_url_base = match.group(1)
                        st.success("✅ 商品ページからレビューリンクの自動発見に成功しました！")
                    else:
                        st.error("❌ 楽天のセキュリティブロックにより、商品ページの裏側にアクセスできませんでした。\n\n💡 **【解決策】** ブラウザで商品の「レビューを見る」をクリックし、**レビュー一覧画面のURL（https://review.rakuten.co.jp/...）をコピーして、直接上の枠に貼り付けて**再度お試しください！")
                        st.stop()

            # ==========================================
            # データ収集処理（ルートA・B共通）
            # ==========================================
            reviews = []
            max_pages = 50 # 最大50ページ（750件）まで自動で進む
            
            progress_bar = st.progress(0)
            status_text = st.empty()

            for page in range(1, max_pages + 1):
                page_url = f"{review_url_base}/1.{page}/"
                status_text.text(f"🏃‍♂️ データ収集進行中... ページ {page} を探索中 (現在 {len(reviews)}件 取得済)")
                
                try:
                    res_p = requests.get(page_url, headers=headers)
                    soup_p = BeautifulSoup(res_p.content, "html.parser")
                    
                    # 楽天の様々なページ構造に対応できる名札リスト
                    review_elements = soup_p.find_all(class_=["revRvwUserEntryTxt", "rev-RvwText", "review-text"])
                    
                    # ページにレビューが1件も無くなったら終了！
                    if not review_elements:
                        break
                        
                    for element in review_elements:
                        text = element.get_text(strip=True)
                        if text:
                            reviews.append({"レビュー本文": text})
                            
                except Exception as e:
                    st.error(f"⚠️ ページ{page}の取得中にエラーが発生しました: {e}")
                    break
                    
                progress_bar.progress(page / max_pages)
                time.sleep(1) # 1ページごとに1秒休憩（重要）

            # ==========================================
            # CSV出力とダウンロード
            # ==========================================
            if len(reviews) > 0:
                progress_bar.progress(1.0)
                df = pd.DataFrame(reviews)
                df.index = df.index + 1
                
                status_text.text(f"🎉 完了しました！ 計 {len(df)} 件のデータを収集しました！！")
                st.dataframe(df)
                
                csv = df.to_csv().encode('utf-8-sig')
                
                st.download_button(
                    label="📥 CSVファイルをダウンロード",
                    data=csv,
                    file_name="rakuten_reviews_complete.csv",
                    mime="text/csv"
                )
            else:
                st.warning("😢 ページにはアクセスできましたが、レビューの文章が見つかりませんでした。")

        except Exception as e:
            st.error(f"❌ 予期せぬエラーが発生しました: {e}")
