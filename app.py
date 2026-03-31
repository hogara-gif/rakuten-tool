import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

# ページの設定
st.set_page_config(page_title="楽天レビュー完全収集ツール", page_icon="📊")

st.title("📊 楽天レビュー完全収集ツール")
st.write("楽天の「レビュー一覧ページURL」を入力してください。無限ループを防止する賢いツールです！")

# Step 1: URLを入力する枠
input_url = st.text_input("ここにURLを貼り付けてください", placeholder="https://review.rakuten.co.jp/item/1/...")

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

            # URLからベース部分を抽出
            match = re.search(r'(https://review\.rakuten\.co\.jp/item/1/\d+_\d+)', input_url)
            if match:
                review_url_base = match.group(1)
                st.success("✅ レビュー専用URLを検知しました！データの収集を開始します。")
            else:
                st.error("❌ レビューURLの形式が正しくありません。\n(例: https://review.rakuten.co.jp/item/1/12345_67890/1.1/)")
                st.stop()

            # ==========================================
            # データ収集処理（ループ防止機能付き）
            # ==========================================
            reviews = []
            seen_texts = set() # 重複をチェックするための「記憶メモリ」
            max_pages = 50 
            
            progress_bar = st.progress(0)
            status_text = st.empty()

            for page in range(1, max_pages + 1):
                page_url = f"{review_url_base}/1.{page}/"
                status_text.text(f"🏃‍♂️ データ収集進行中... ページ {page} を探索中 (現在 {len(reviews)}件 取得済)")
                
                try:
                    res_p = requests.get(page_url, headers=headers)
                    soup_p = BeautifulSoup(res_p.content, "html.parser")
                    
                    review_blocks = soup_p.find_all('li')
                    new_reviews_count = 0 # このページで新しく見つけた件数
                    
                    for block in review_blocks:
                        body_element = block.find(class_=["review-body--LpVR4", "no-ellipsis--2jV9-"])
                        
                        if body_element:
                            text = body_element.get_text(separator='\n', strip=True)
                            
                            # ★ここで重複チェック！まだ見たことのない文章だけを保存する
                            if text and text not in seen_texts:
                                seen_texts.add(text) # 記憶に保存
                                
                                shop_comment_element = block.find(class_="shop-comment-body--3WU17")
                                shop_comment = shop_comment_element.get_text(separator='\n', strip=True) if shop_comment_element else ""
                                
                                reviews.append({
                                    "レビュー本文": text,
                                    "ショップからのコメント": shop_comment
                                })
                                new_reviews_count += 1

                    # もし「新しいレビュー」が1件も無かったら、楽天のループ罠にハマったと判断して終了！
                    if new_reviews_count == 0:
                        break
                            
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
                
                status_text.text(f"🎉 大成功です！！ 重複を除外し、計 {len(df)} 件のデータを収集しました！！")
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
