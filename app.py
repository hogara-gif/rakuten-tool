import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import math
import time
import re

# ページの設定
st.set_page_config(page_title="楽天レビュー完全収集ツール", page_icon="📊")

st.title("📊 楽天レビュー完全収集ツール")
st.write("商品ページのURLを入力するだけで、レビュー専用ページを自動で探し出し、全件一括収集します！")

# Step 1: URLを入力する枠
input_url = st.text_input("楽天の「商品ページURL」を貼り付けてください", placeholder="https://item.rakuten.co.jp/norganic/nb-trialkitset-01/")

# ボタンを押した時の動き
if st.button("データ収集開始"):
    if not input_url:
        st.warning("⚠️ URLが入力されていません！")
    else:
        # 楽天に怪しまれないためのヘッダー
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
        }

        try:
            # ==========================================
            # Step 2 & 3: 商品ページから直接リンクと件数を取得
            # ==========================================
            with st.spinner("商品ページを解析し、レビューリンクを探しています..."):
                res = requests.get(input_url, headers=headers)
                if res.status_code != 200:
                    st.error(f"❌ 商品ページへのアクセスに失敗しました（エラーコード: {res.status_code}）")
                    st.stop()
                
                soup = BeautifulSoup(res.content, "html.parser")
                
                review_url_base = None
                total_reviews = 0
                
                # ユーザー様ご指摘の、一番確実な <a> タグを直接探す
                review_link_tag = soup.find('a', href=re.compile(r'https://review\.rakuten\.co\.jp/item/1/'))
                
                if review_link_tag:
                    # ① href からベースとなるURLを抽出
                    href = review_link_tag.get('href', '')
                    match_url = re.search(r'(https://review\.rakuten\.co\.jp/item/1/\d+_\d+)', href)
                    if match_url:
                        review_url_base = match_url.group(1)
                    
                    # ② aria-label (例: "(41件)") から件数を抽出
                    aria_label = review_link_tag.get('aria-label', '')
                    match_count = re.search(r'([0-9,]+)', aria_label)
                    if match_count:
                        total_reviews = int(match_count.group(1).replace(',', ''))
                
                # 万が一、古いページデザイン等で見つからなかった場合の予備（フォールバック）
                if not review_url_base or total_reviews == 0:
                    review_count_meta = soup.find("meta", {"itemprop": "reviewCount"})
                    if review_count_meta:
                        total_reviews = int(review_count_meta.get("content", 0))
                    
                    shop_bid_input = soup.find("input", {"name": "shop_bid"})
                    item_id_input = soup.find("input", {"name": "item_id"})
                    if shop_bid_input and item_id_input:
                        review_url_base = f"https://review.rakuten.co.jp/item/1/{shop_bid_input.get('value')}_{item_id_input.get('value')}"

                # 最終チェック
                if not review_url_base or total_reviews == 0:
                    st.error("❌ レビューが見つからないか、まだ投稿されていないようです。別の商品のURLでお試しください。")
                    st.stop()

            st.success(f"✅ レビューリンクを特定しました！ 総レビュー数: {total_reviews}件")

            # ==========================================
            # Step 4: レビュー取得と進捗表示
            # ==========================================
            reviews = []
            # 楽天レビューは1ページあたり15件表示
            pages_to_fetch = math.ceil(total_reviews / 15)
            
            # サーバー負荷対策として、最大取得ページ数を設定（例: 最大50ページ＝750件まで）
            max_pages = min(pages_to_fetch, 50)
            
            progress_bar = st.progress(0)
            status_text = st.empty()

            for page in range(1, max_pages + 1):
                # ベースURLに /1.1/ や /1.2/ をくっつけてページめくり
                page_url = f"{review_url_base}/1.{page}/"
                status_text.text(f"データ収集進行中... ページ {page}/{max_pages} 処理中 (現在 {len(reviews)}件 取得済)")
                
                try:
                    res_p = requests.get(page_url, headers=headers)
                    soup_p = BeautifulSoup(res_p.content, "html.parser")
                    
                    # レビューの文章部分を抽出（複数のクラス名に対応）
                    review_elements = soup_p.find_all(class_=["revRvwUserEntryTxt", "rev-RvwText", "review-text"])
                    
                    if not review_elements:
                        break
                        
                    for element in review_elements:
                        text = element.get_text(strip=True)
                        if text:
                            reviews.append({"レビュー本文": text})
                            
                except Exception as e:
                    st.error(f"⚠️ ページ{page}の取得中にエラーが発生しました: {e}")
                    break
                    
                # 進捗バーの更新
                progress_bar.progress(page / max_pages)
                time.sleep(1) # 1ページごとに1秒休憩（サーバー負荷軽減）

            # ==========================================
            # Step 5: CSV出力とダウンロード
            # ==========================================
            if len(reviews) > 0:
                df = pd.DataFrame(reviews)
                df.index = df.index + 1 # 行番号を1からにする
                
                status_text.text(f"🎉 完了しました！ 計 {len(df)} 件のデータを収集しました。")
                st.dataframe(df)
                
                # 文字化け防止の utf-8-sig
                csv = df.to_csv().encode('utf-8-sig')
                
                st.download_button(
                    label="📥 CSVファイルをダウンロード",
                    data=csv,
                    file_name="rakuten_reviews_complete.csv",
                    mime="text/csv"
                )
            else:
                st.warning("😢 レビュー本文の抽出に失敗しました。ページ構造が変更された可能性があります。")

        except Exception as e:
            st.error(f"❌ 予期せぬエラーが発生しました: {e}")
