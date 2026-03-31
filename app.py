import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

st.set_page_config(page_title="楽天レビュー完全収集ツール", page_icon="📊", layout="wide")

st.title("📊 楽天レビュー完全収集ツール")
st.write("楽天の「レビュー一覧ページURL」を入力してください。動的なクラス名にも対応した最新版です！")

input_url = st.text_input("ここにURLを貼り付けてください", placeholder="https://review.rakuten.co.jp/item/1/...")

if st.button("データ収集開始"):
    if not input_url:
        st.warning("⚠️ URLが入力されていません！")
    else:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
        }

        try:
            # URLからベース部分を抽出
            match = re.search(r'(https://review\.rakuten\.co\.jp/item/1/\d+_\d+)', input_url)
            if match:
                review_url_base = match.group(1)
                st.success("✅ レビュー専用URLを検知しました！")
            else:
                st.error("❌ URLの形式が正しくありません。")
                st.stop()

            reviews = []
            seen_reviews = set()
            max_pages = 50 
            
            progress_bar = st.progress(0)
            status_text = st.empty()

            for page in range(1, max_pages + 1):
                # 強制的に「新着順（6）」でアクセス
                page_url = f"{review_url_base}/6.{page}/"
                status_text.text(f"🏃‍♂️ ページ {page} を解析中... (現在 {len(reviews)}件 取得済)")
                
                try:
                    res_p = requests.get(page_url, headers=headers)
                    soup_p = BeautifulSoup(res_p.content, "html.parser")
                    
                    # 💡 【重要】特定の名前ではなく「その言葉が含まれているか」で探す（正規表現を使用）
                    # これにより --LpVR4 のようなランダム文字列を無視できます
                    items = soup_p.find_all(class_=re.compile(r"container--1yx5R")) # レビュー1件の塊
                    
                    if not items:
                        # もし塊が見つからない場合は、予備で li タグを全部見る
                        items = soup_p.find_all("li")

                    new_on_this_page = 0
                    
                    for item in items:
                        # 1. レビュー本文 (review-body-- か no-ellipsis-- で始まるクラスを探す)
                        body_el = item.find(class_=re.compile(r"review-body--|no-ellipsis--"))
                        if not body_el:
                            continue
                        
                        text = body_el.get_text(separator='\n', strip=True)
                        
                        # 2. 投稿日 (4桁/2桁/2桁 の形式を探す)
                        date_el = item.find(string=re.compile(r'\d{4}/\d{2}/\d{2}'))
                        date = date_el.strip() if date_el else ""
                        
                        # 3. 評価 (数字が入っているクラスを探す)
                        rating_el = item.find("span", class_=re.compile(r"font-fixed--"))
                        rating = rating_el.get_text(strip=True) if rating_el else ""
                        
                        # 4. ショップからのコメント (shop-comment-body-- で始まるクラス)
                        shop_comment_el = item.find(class_=re.compile(r"shop-comment-body--"))
                        shop_comment = shop_comment_el.get_text(separator='\n', strip=True) if shop_comment_el else ""

                        # 重複チェック（本文と日付で判定）
                        review_id = (date, text)
                        if text and review_id not in seen_reviews:
                            seen_reviews.add(review_id)
                            reviews.append({
                                "投稿日": date,
                                "評価": rating,
                                "レビュー本文": text,
                                "ショップからのコメント": shop_comment
                            })
                            new_on_this_page += 1

                    if new_on_this_page == 0:
                        # これ以上新しいレビューがないなら終了
                        break
                            
                except Exception as e:
                    st.error(f"⚠️ エラー: {e}")
                    break
                    
                progress_bar.progress(min(page / 5, 1.0)) # 進捗バーを少しずつ進める
                time.sleep(1)

            if len(reviews) > 0:
                progress_bar.progress(1.0)
                df = pd.DataFrame(reviews)
                df.index = df.index + 1
                status_text.text(f"🎉 完了！ 計 {len(df)} 件のレビューを取得しました。")
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv().encode('utf-8-sig')
                st.download_button("📥 CSVファイルをダウンロード", data=csv, file_name="rakuten_reviews.csv", mime="text/csv")
            else:
                st.warning("😢 ページ構造がさらに変更された可能性があります。")
                # デバッグ用に取得したHTMLの冒頭を表示（困った時のヒント用）
                if 'res_p' in locals():
                    st.code(res_p.text[:500], language="html")

        except Exception as e:
            st.error(f"❌ 致命的なエラー: {e}")
