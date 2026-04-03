import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json

st.set_page_config(page_title="楽天レビュー完全収集ツール", page_icon="📊", layout="wide")
st.title("📊 楽天レビュー完全収集ツール (SPA完全対応版)")
st.write("解析により判明した「隠しデータ（JSON）」から全件を抽出する最終形態です！")

input_url = st.text_input("レビュー一覧URLを貼り付けてください", placeholder="https://review.rakuten.co.jp/item/1/...")

if st.button("データ収集開始"):
    if not input_url:
        st.warning("⚠️ URLを入力してください")
        st.stop()
        
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    }

    try:
        match = re.search(r'item/1/(\d+_\d+)', input_url)
        if not match:
            st.error("❌ URLの形式が正しくありません")
            st.stop()
        
        item_id = match.group(1)
        all_reviews = []
        seen_texts = set()

        progress_bar = st.progress(0)
        status_text = st.empty()

        # 💡 隠しデータ（JSON）の迷宮からレビューを探し出す魔法の関数
        def extract_from_json(obj):
            extracted = []
            if isinstance(obj, dict):
                # 楽天のJSON内でレビュー本文が入りそうなキーを探す
                body = obj.get('body') or obj.get('reviewBody') or obj.get('comment')
                if body and isinstance(body, str) and len(body) > 2:
                    rating = obj.get('rating') or obj.get('reviewRating', {}).get('ratingValue') or ""
                    date = obj.get('insertDate') or obj.get('createDate') or ""
                    extracted.append({"投稿日": date, "評価": rating, "レビュー本文": body})
                for k, v in obj.items():
                    extracted.extend(extract_from_json(v))
            elif isinstance(obj, list):
                for item in obj:
                    extracted.extend(extract_from_json(item))
            return extracted

        # 最大10ページ（150件）まで探索
        for page in range(1, 11):
            # 新着順（6.x）でリクエストし、隠しデータを引っ張り出す
            page_url = f"https://review.rakuten.co.jp/item/1/{item_id}/6.{page}/"
            status_text.text(f"🏃‍♂️ 隠しデータを解析中... ページ {page} (現在 {len(all_reviews)}件)")
            
            try:
                res = requests.get(page_url, headers=headers, timeout=10)
                soup = BeautifulSoup(res.content, "html.parser")
                
                new_found = 0
                
                # 1. まずはHTMLから探す（SEO用の保険）
                html_elements = soup.find_all(class_=re.compile(r"review-body|no-ellipsis|revRvwUserEntryTxt"))
                for el in html_elements:
                    text = el.get_text(separator='\n', strip=True)
                    if len(text) > 2 and text not in seen_texts:
                        seen_texts.add(text)
                        all_reviews.append({"レビュー本文": text})
                        new_found += 1
                        
                # 2. 【本命】HTMLが空っぽなら、隠しデータ(JSON)をこじ開ける！
                if new_found == 0:
                    for script in soup.find_all('script'):
                        if script.string and 'window.__INITIAL_STATE__' in script.string:
                            try:
                                # JSON部分だけを綺麗に切り取る
                                json_str = script.string.split('window.__INITIAL_STATE__ = ')[1].strip()
                                if json_str.endswith(';'):
                                    json_str = json_str[:-1]
                                
                                json_data = json.loads(json_str)
                                json_reviews = extract_from_json(json_data)
                                
                                for r in json_reviews:
                                    text = r["レビュー本文"]
                                    if text not in seen_texts:
                                        # ゴミデータを除去
                                        if any(x in text for x in ["レビューを書く", "並び替え"]):
                                            continue
                                        seen_texts.add(text)
                                        # JSONから取れた場合は日付と評価も追加
                                        all_reviews.append({"投稿日": r["投稿日"], "評価": r["評価"], "レビュー本文": text})
                                        new_found += 1
                            except Exception as e:
                                pass # JSONのパースエラーはスキップ
                            break # スクリプトを見つけたらループを抜ける
                            
                # どちらの方法でも新しいレビューが見つからなければ終了
                if new_found == 0:
                    break
                    
            except Exception as e:
                break
                
            progress_bar.progress(min(page / 10, 1.0))
            time.sleep(1.5)

        if len(all_reviews) > 0:
            progress_bar.progress(1.0)
            df = pd.DataFrame(all_reviews)
            
            # 列の順番を整える
            if "投稿日" in df.columns:
                df = df[["投稿日", "評価", "レビュー本文"]]
            
            st.success(f"🎉 大成功！ JSONとHTMLのハイブリッド解析で {len(df)} 件を取得しました！")
            st.dataframe(df, use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 CSVファイルをダウンロード", data=csv, file_name="rakuten_reviews_final.csv")
        else:
            st.error("❗ データの取得に失敗しました。")

    except Exception as e:
        st.error(f"❌ 予期せぬエラー: {e}")
