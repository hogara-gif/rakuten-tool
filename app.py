import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# ページの設定
st.set_page_config(page_title="楽天レビュー収集ツール", page_icon="🛒")

st.title("🛒 楽天レビュー自動収集ツール")
st.write("楽天の商品URLを入力すると、レビューを自動で収集してCSVで保存できます！")

# URLを入力する枠
url = st.text_input("楽天の商品URLを貼り付けてください", placeholder="https://item.rakuten.co.jp/...")

# ボタンを押した時の動き
if st.button("レビューを収集する"):
    if not url:
        st.warning("⚠️ URLが入力されていません！")
    else:
        with st.spinner("裏側で一生懸命データを集めています...（数十秒かかる場合があります）"):
            try:
                # 楽天に怪しまれないように、普通のブラウザのふりをする設定
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
                }
                
                # 楽天のページにアクセスしてデータを取ってくる
                response = requests.get(url, headers=headers)
                soup = BeautifulSoup(response.content, "html.parser")
                
                reviews = []
                
                # レビューの文章が書かれている部分を探す
                # （※楽天のサイト構造によってはうまく取れない場合があります）
                review_elements = soup.find_all(class_="rev-RvwText")
                
                if len(review_elements) == 0:
                    st.info("😢 このページからはレビューが見つかりませんでした。別の商品のURLで試してみてください。")
                else:
                    for idx, element in enumerate(review_elements):
                        text = element.get_text(strip=True)
                        reviews.append({
                            "番号": idx + 1,
                            "レビュー本文": text
                        })
                    
                    # データを表（データフレーム）に変換
                    df = pd.DataFrame(reviews)
                    
                    st.success(f"🎉 {len(df)}件のレビューを収集しました！")
                    
                    # 画面に表を表示
                    st.dataframe(df)
                    
                    # CSVダウンロード用のデータを作成（文字化け防止の utf-8-sig）
                    csv = df.to_csv(index=False).encode('utf-8-sig')
                    
                    # ダウンロードボタンを表示
                    st.download_button(
                        label="📥 CSVファイルをダウンロード",
                        data=csv,
                        file_name="rakuten_reviews.csv",
                        mime="text/csv"
                    )
            except Exception as e:
                st.error(f"❌ エラーが発生しました: {e}")
