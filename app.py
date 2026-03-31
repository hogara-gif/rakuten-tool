import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

# ページの設定
st.set_page_config(page_title="楽天レビュー完全収集ツール", page_icon="📊", layout="wide")

st.title("📊 楽天レビュー完全収集ツール")
st.write("楽天の「レビュー一覧ページURL」を入力してください。「新着順」で全件根こそぎ取得します！")

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

            # URLからショップIDとアイテムIDのベース部分を抽出
            match = re.search(r'(https://review\.rakuten\.co\.jp/item/1/\d+_\d+)', input_url)
            if match:
                review_url_base = match.group(1)
                st.success("✅ レビュー専用URLを検知しました！データの収集を開始します。")
            else:
                st.error("❌ レビューURLの形式が正しくありません。\n(例: https://review.rakuten.co.jp/item/1/12345_67890/1.1/)")
                st.stop()

            # ==========================================
            # データ収集処理（強制『新着順（6）』で全件取得！）
            # ==========================================
            reviews = []
            seen_reviews = set() # 重複チェック用メモリ
            max_pages = 50 
            
            progress_bar = st.progress(0)
            status_text = st.empty()

            for page in range(1, max_pages + 1):
                # 💡【最大のポイント】最初の数字を「6」にすることで「新着順」になり、隠されたレビューも全て表示されます
                page_url = f"{review_url_base}/6.{page}/"
                status_text.text(f"🏃‍♂️ データ収集進行中... ページ {page} を探索中 (現在 {len(reviews)}件 取得済)")
                
                try:
                    res_p = requests.get(page_url, headers=headers)
                    soup_p = BeautifulSoup(res_p.content, "html.parser")
                    
                    review_blocks = soup_p.find_all('li')
                    new_reviews_count = 0
                    
                    for block in review_blocks:
                        # レビューのヘッダー（日付や星がある場所）を探す
                        header_element = block.find(class_="header--1B1vT")
                        if not header_element:
                            continue # ヘッダーがないliタグはレビューではないのでスキップ
                            
                        # 1. 評価（星の数）
                        rating_el = header_element.find("span", class_=re.compile("font-fixed"))
                        rating = rating_el.get_text(strip=True) if rating_el else ""
                        
                        # 2. 投稿日
                        date_el = header_element.find(string=re.compile(r'\d{4}/\d{2}/\d{2}'))
                        date = date_el.strip() if date_el else ""
                        
                        # 3. 投稿者名
                        name_el = block.find(class_=re.compile("reviewer-name--"))
                        name = name_el.get_text(strip=True) if name_el else "購入者さん"
                        
                        # 4. タイトル
                        title_el = block.find("div", class_=re.compile("type-header--"))
                        title = title_el.get_text(strip=True) if title_el else ""
                        
                        # 5. 本文（本文がない「星のみ」のレビューも許容する）
                        body_el = block.find(class_=["review-body--LpVR4", "no-ellipsis--2jV9-"])
                        text = body_el.get_text(separator='\n', strip=True) if body_el else ""
                        
                        # 6. ショップからのコメント
                        shop_comment_el = block.find(class_="shop-comment-body--3WU17")
                        shop_comment = shop_comment_el.get_text(separator='\n', strip=True) if shop_comment_el else ""
                        
                        # 重複チェック用にデータをまとめる
                        review_tuple = (date, rating, name, title, text)
                        
                        if review_tuple not in seen_reviews:
                            seen_reviews.add(review_tuple)
                            reviews.append({
                                "投稿日": date,
                                "評価": rating,
                                "投稿者": name,
                                "タイトル": title,
                                "レビュー本文": text,
                                "ショップからのコメント": shop_comment
                            })
                            new_reviews_count += 1

                    # 新しいレビューが1件も見つからなければ終了
                    if new_reviews_count == 0:
                        break
                            
                except Exception as e:
                    st.error(f"⚠️ ページ{page}の取得中にエラーが発生しました: {e}")
                    break
                    
                progress_bar.progress(page / max_pages)
                time.sleep(1)

            # ==========================================
            # CSV出力とダウンロード
            # ==========================================
            if len(reviews) > 0:
                progress_bar.progress(1.0)
                df = pd.DataFrame(reviews)
                df.index = df.index + 1
                
                status_text.text(f"🎉 大成功です！！ 隠されていたレビューも含め、計 {len(df)} 件のデータを収集しました！！")
                st.dataframe(df)
                
                csv = df.to_csv().encode('utf-8-sig')
                
                st.download_button(
                    label="📥 CSVファイルをダウンロード",
                    data=csv,
                    file_name="rakuten_reviews_complete.csv",
                    mime="text/csv"
                )
            else:
                st.warning("😢 ページにはアクセスできましたが、レビューが見つかりませんでした。")

        except Exception as e:
            st.error(f"❌ 予期せぬエラーが発生しました: {e}")
