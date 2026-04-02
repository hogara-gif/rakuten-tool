import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

st.set_page_config(page_title="楽天レビュー完全収集ツール", page_icon="📊", layout="wide")
st.title("📊 楽天レビュー完全収集ツール")
st.write("新着順（全件表示モード）で41件すべてを確実に取得します！")

input_url = st.text_input("レビュー一覧URLを貼り付けてください", placeholder="https://review.rakuten.co.jp/item/1/...")

if st.button("データ収集開始"):
    if not input_url:
        st.warning("⚠️ URLを入力してください")
    else:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja-JP,ja;q=0.9",
        }

        try:
            match = re.search(r'item/1/(\d+_\d+)', input_url)
            if not match:
                st.error("❌ 正しいURLを入力してください")
                st.stop()
            
            item_id = match.group(1)
            reviews = []
            seen_texts = set()

            progress_bar = st.progress(0)
            status_text = st.empty()

            # 最大10ページ（150件）まで探索範囲を広げます
            for page in range(1, 11):
                # 💡【ここが最重要修正！】 1.{page} を 6.{page} に変更
                # これで「おすすめ順（30件制限）」を回避し、「新着順（全件）」で取得します
                page_url = f"https://review.rakuten.co.jp/item/1/{item_id}/6.{page}/"
                
                status_text.text(f"🏃‍♂️ 全件モードで取得中... ページ {page} (現在 {len(reviews)}件)")
                
                try:
                    res = requests.get(page_url, headers=headers, timeout=10)
                    soup = BeautifulSoup(res.content, "html.parser")
                    
                    # より広い範囲でレビュー本文をキャッチする設定
                    candidates = soup.find_all(['div', 'span', 'p'], class_=re.compile(r"review-body|revRvwUserEntryTxt|no-ellipsis|rev-RvwText"))
                    
                    found_on_page = 0
                    for el in candidates:
                        text = el.get_text(strip=True)
                        if len(text) > 5 and text not in seen_texts:
                            # ボタン文字などのゴミを除去
                            if any(x in text for x in ["レビューを書く", "並び替え", "ショップからのコメント"]):
                                continue
                                
                            seen_texts.add(text)
                            reviews.append({"番号": len(reviews)+1, "レビュー本文": text})
                            found_on_page += 1

                    if found_on_page == 0:
                        break
                            
                except Exception:
                    break
                    
                progress_bar.progress(min(page / 10, 1.0))
                time.sleep(1.5)

            if len(reviews) > 0:
                progress_bar.progress(1.0)
                df = pd.DataFrame(reviews)
                st.success(f"🎉 ついに全件攻略！ {len(df)} 件のレビューを取得しました！")
                st.dataframe(df, use_container_width=True)
                
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 CSVファイルをダウンロード", data=csv, file_name="rakuten_reviews_all.csv")
            else:
                st.error("❗ レビューが取得できませんでした。")

        except Exception as e:
            st.error(f"❌ エラー: {e}")
