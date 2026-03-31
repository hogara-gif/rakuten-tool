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
        # 楽天に怪しまれないための強力なヘッダー
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        }

        try:
            # ==========================================
            # Step 2 & 3: 商品ページからURLと件数を探索
            # ==========================================
            with st.spinner("商品ページを解析し、レビューリンクを探しています..."):
                res = requests.get(input_url, headers=headers)
                if res.status_code != 200:
                    st.error(f"❌ 商品ページへのアクセスに失敗しました（エラーコード: {res.status_code}）")
                    st.stop()
                
                html_text = res.text
                soup = BeautifulSoup(html_text, "html.parser")
                
                review_url_base = None
                total_reviews = 0
                
                # 探索ルート1: <a>タグ（リンク）から探す
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    if 'review.rakuten.co.jp/item/1/' in href:
                        match = re.search(r'(https://review\.rakuten\.co\.jp/item/1/\d+_\d+)', href)
                        if match:
                            review_url_base = match.group(1)
                            # 件数もついでに探す
                            aria = a_tag.get('aria-label', '')
                            text = a_tag.get_text(strip=True)
                            m_count = re.search(r'([0-9,]+)件', aria) or re.search(r'([0-9,]+)件', text)
                            if m_count:
                                total_reviews = int(m_count.group(1).replace(',', ''))
                            break
                
                # 探索ルート2: 隠しデータ（inputタグ）から探す
                if not review_url_base:
                    shop_bid_input = soup.find("input", attrs={"name": "shop_bid"})
                    item_id_input = soup.find("input", attrs={"name": "item_id"})
                    if shop_bid_input and item_id_input:
                        shop_id = shop_bid_input.get("value")
                        item_id = item_id_input.get("value")
                        review_url_base = f"https://review.rakuten.co.jp/item/1/{shop_id}_{item_id}"

                # 探索ルート3: HTMLの文字全体から無理やり探す（最終奥義）
                if not review_url_base:
                    shop_match = re.search(r'shop_bid["\s=>]+(\d{6,})', html_text)
                    item_match = re.search(r'item_id["\s=>]+(\d{6,})', html_text)
                    if shop_match and item_match:
                        review_url_base = f"https://review.rakuten.co.jp/item/1/{shop_match.group(1)}_{item_match.group(1)}"

                # さすがにURLが全く見つからなければ終了
                if not review_url_base:
                    st.error("❌ レビューのURLを特定できませんでした。楽天側でブロックされている可能性があります。")
                    st.stop()

                # 件数が見つかっていない場合、メタタグからも探す
                if total_reviews == 0:
                    meta_review = soup.find("meta", attrs={"itemprop": "reviewCount"})
                    if meta_review and meta_review.get("content"):
                        total_reviews = int(meta_review.get("content", 0))

            # 件数が分からなくてもストップさせずに進む！
            if total_reviews > 0:
                st.success(f"✅ レビューリンクを特定しました！ (想定レビュー数: {total_reviews}件)")
                max_pages = math.ceil(total_reviews / 15)
            else:
                st.success("✅ レビューリンクを特定しました！ (件数不明のため、最後まで自動で探索します)")
                max_pages = 50 # わからない場合は最大50ページ（750件）まで探す

            # ==========================================
            # Step 4: レビュー取得と進捗表示
            # ==========================================
            reviews = []
            max_pages = min(max_pages, 50) # サーバー負荷対策で最大50ページ上限
            
            progress_bar = st.progress(0)
            status_text = st.empty()

            for page in range(1, max_pages + 1):
                page_url = f"{review_url_base}/1.{page}/"
                status_text.text(f"データ収集進行中... ページ {page} を探索中 (現在 {len(reviews)}件 取得済)")
                
                try:
                    res_p = requests.get(page_url, headers=headers)
                    soup_p = BeautifulSoup(res_p.content, "html.parser")
                    
                    review_elements = soup_p.find_all(class_=["revRvwUserEntryTxt", "rev-RvwText", "review-text"])
                    
                    # ページにレビューが1件も無くなったら、最後のページまで到達したと判断して終了（大成功）
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
                time.sleep(1) # 1ページごとに1秒休憩

            # ==========================================
            # Step 5: CSV出力とダウンロード
            # ==========================================
            if len(reviews) > 0:
                progress_bar.progress(1.0) # バーを100%にする
                df = pd.DataFrame(reviews)
                df.index = df.index + 1
                
                status_text.text(f"🎉 完了しました！ 計 {len(df)} 件のデータを収集しました。")
                st.dataframe(df)
                
                csv = df.to_csv().encode('utf-8-sig')
                
                st.download_button(
                    label="📥 CSVファイルをダウンロード",
                    data=csv,
                    file_name="rakuten_reviews_complete.csv",
                    mime="text/csv"
                )
            else:
                st.warning("😢 レビューページにはアクセスできましたが、本文がうまく抽出できませんでした。")

        except Exception as e:
            st.error(f"❌ 予期せぬエラーが発生しました: {e}")
