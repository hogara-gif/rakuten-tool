import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

st.set_page_config(page_title="楽天レビュー収集ツール", page_icon="📊", layout="wide")
st.title("📊 楽天レビュー収集ツール (安定・最終版)")
st.write("※楽天のシステム制限により、HTML上に公開されている上位レビュー（最大30件）を確実かつ綺麗に取得します。")

input_url = st.text_input("レビュー一覧URLを貼り付けてください", placeholder="https://review.rakuten.co.jp/item/1/...")

if st.button("データ収集開始"):
    if not input_url:
        st.warning("⚠️ URLを入力してください")
    else:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
        }

        try:
            match = re.search(r'item/1/(\d+_\d+)', input_url)
            if not match:
                st.error("❌ URLの形式が正しくありません")
                st.stop()
            
            item_id = match.group(1)
            reviews = []
            seen_texts = set()

            progress_bar = st.progress(0)
            status_text = st.empty()

            # 標準順(1.x)で、HTMLが提供される限界（実質2〜3ページ）まで探索
            for page in range(1, 6):
                page_url = f"https://review.rakuten.co.jp/item/1/{item_id}/1.{page}/"
                status_text.text(f"🏃‍♂️ データを取得中... ページ {page} (現在 {len(reviews)}件)")
                
                try:
                    res = requests.get(page_url, headers=headers, timeout=10)
                    soup = BeautifulSoup(res.content, "html.parser")
                    
                    # レビューの塊を探す
                    review_blocks = soup.find_all(class_=re.compile(r"container--1yx5R"))
                    if not review_blocks:
                        review_blocks = soup.find_all("li")

                    found_count = 0
                    for block in review_blocks:
                        # 本文
                        body_el = block.find(class_=re.compile(r"review-body|no-ellipsis|revRvwUserEntryTxt"))
                        text = body_el.get_text(separator='\n', strip=True) if body_el else ""
                        
                        # 評価
                        rating_el = block.find("span", class_=re.compile(r"font-fixed"))
                        rating = rating_el.get_text(strip=True) if rating_el else ""
                        
                        # 投稿日
                        date_el = block.find(string=re.compile(r'\d{4}/\d{2}/\d{2}'))
                        date = date_el.strip() if date_el else ""
                        
                        # ショップコメント
                        shop_comment_el = block.find(class_=re.compile(r"shop-comment-body"))
                        shop_comment = shop_comment_el.get_text(separator='\n', strip=True) if shop_comment_el else ""

                        if text and text not in seen_texts:
                            # 無関係なボタン等の文字を除外
                            if any(x in text for x in ["レビューを書く", "並び替え", "不適切レビュー報告"]):
                                continue
                            seen_texts.add(text)
                            reviews.append({
                                "投稿日": date,
                                "評価": rating,
                                "レビュー本文": text,
                                "ショップからのコメント": shop_comment
                            })
                            found_count += 1
                    
                    # このページで1件も新しいレビューが見つからなければ、楽天の表示限界と判断して終了
                    if found_count == 0:
                        break
                        
                except Exception:
                    break
                    
                progress_bar.progress(page / 5)
                time.sleep(1.5)

            if len(reviews) > 0:
                progress_bar.progress(1.0)
                df = pd.DataFrame(reviews)
                df.index = df.index + 1
                
                st.success(f"🎉 完了しました！ {len(df)} 件のレビューを安定して取得しました。")
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 CSVファイルをダウンロード", data=csv, file_name="rakuten_reviews_stable.csv", mime="text/csv")
            else:
                st.error("❗ レビューが取得できませんでした。")

        except Exception as e:
            st.error(f"❌ エラー発生: {e}")
