import streamlit as st
import requests
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="楽天レビュー徹底解析", layout="wide")
st.title("🕵️‍♂️ 楽天レビュー 徹底解析ツール")
st.write("憶測をやめ、楽天のページ構造（プログラムからの見え方）を直接丸裸にします。")

input_url = st.text_input("レビュー一覧URLを貼り付けてください", value="https://review.rakuten.co.jp/item/1/355020_10000241/1.1/?l2-id=item_review")

if st.button("ページを解析する"):
    with st.spinner("ページの生データを取得中..."):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        }
        res = requests.get(input_url, headers=headers)
        soup = BeautifulSoup(res.content, "html.parser")
        
        st.write("---")
        
        # 【調査1】純粋にこのページから何件のテキストが見つかるか
        st.subheader("1. この1ページ目から取得できたレビュー数")
        review_elements = soup.find_all(class_=re.compile(r"review-body|no-ellipsis|revRvwUserEntryTxt"))
        st.write(f"👉 **{len(review_elements)} 件** のテキスト要素が見つかりました。（通常は15件のはずです）")
        
        # 【調査2】ページ送りのURLがどうなっているか
        st.subheader("2. 「次へ」や「2ページ目」のリンク（超重要）")
        st.write("プログラムが2ページ目に進むための正しいURLを探します。")
        page_links = set()
        for a in soup.find_all('a', href=True):
            href = a['href']
            # ページ番号っぽいリンクを抽出
            if "review.rakuten.co.jp" in href and re.search(r'\d\.\d', href):
                text = a.get_text(strip=True)
                if text: # 文字があるボタンだけ
                    page_links.add((text, href))
        
        if page_links:
            for text, link in page_links:
                st.code(f"ボタン文字: [{text}]\nURL: {link}")
        else:
            st.warning("⚠️ ページ送りのリンクが見つかりません！（URLが変わらないSPA方式の可能性があります）")

        # 【調査3】隠しデータ（JSON）が埋まっていないか
        st.subheader("3. 隠されたデータ（JSON / APIの代わり）の有無")
        st.write("最新のWebサイトは、HTMLの中に全件のデータを『暗号のような文字の塊（JSON）』として隠し持っていることがあります。")
        json_found = False
        for script in soup.find_all('script'):
            content = script.string
            if content and ('__NEXT_DATA__' in content or 'window.__' in content or '"review"' in content):
                # 怪しいスクリプトを発見したらプレビュー表示
                if len(content) > 1000:
                    st.success("🎯 大量にデータが詰まった隠しスクリプトを発見しました！")
                    st.text_area("データの一部プレビュー", content[:1500] + "\n\n... (省略)", height=200)
                    json_found = True
                    break
        
        if not json_found:
            st.info("隠しデータは見つかりませんでした。純粋なHTMLのようです。")
