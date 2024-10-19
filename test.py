import os
import streamlit as st
import google.generativeai as genai
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import urllib.parse
import tiktoken

def get_information(html):
    # API Keyをセット
    genai.configure(api_key=st.secrets["gemini_key"])
    trimmed_html = trim_html_content(html_content=html)
    # プロンプトの作成
    prompt = f"""これらはあるECサイトのHTML文です。
                {trimmed_html}
                HTMLの内容から、これがどのようなwebサイトで、どのような情報が載っているか解析してください。
                回答は、ページ内容を一言で教えてください。
                例１：「これは楽天市場の会員登録ページです。」
                例２：「これはAmazonのインテリアの商品一覧ページです。ページ内にはいくつかの商品情報が含まれます。
                　　　　例）ソファー　10,000円など」
                ・・・
                """
    # モデルを指定してコンテンツを生成
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content(prompt)
    
    # 結果を表示
    return response.text

# URL内の全aタグ情報を取得
def get_links(url):
    # ヘッダーを設定
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # リクエストが成功したかどうかを確認
        soup = BeautifulSoup(response.text, 'html.parser')
        # アクセス元のドメインを取得
        base_domain = urlparse(url).netloc
        # ページ内のすべてのリンクを取得
        links = soup.find_all('a', href=True)
        # すべてのリンクを取得し、外部リンクは除外して保存
        link_data = []
        for link in links:
            full_url = urljoin(url, link['href'])  # 相対リンクを絶対URLに変換
            full_url = normalize_url(full_url)  # URLを正規化
            link_domain = urlparse(full_url).netloc  # リンクのドメイン部分を取得
            # 同じドメインのリンクのみ保存
            if link_domain == base_domain:
                link_data.append(full_url)  # URLのみをリストに追加
        return link_data
    
    except requests.exceptions.RequestException as e:
        return []

# URLを正規化
def normalize_url(url):
    # URLをパース
    parsed_url = urllib.parse.urlparse(url)
    # スキーム（http or https）を小文字に変換
    scheme = parsed_url.scheme.lower()
    # ネットロケーション（ホスト部分）を小文字に変換
    netloc = parsed_url.netloc.lower()
    # 標準ポートを削除 (httpなら80, httpsなら443)
    if scheme == 'http' and netloc.endswith(':80'):
        netloc = netloc[:-3]  # ':80' を削除
    elif scheme == 'https' and netloc.endswith(':443'):
        netloc = netloc[:-4]  # ':443' を削除
    
    # パスの末尾のスラッシュを統一
    path = parsed_url.path
    #if not path.endswith('/'):
    #    path += '/'
    # クエリパラメータやフラグメントはソートして統一
    query = urllib.parse.urlencode(sorted(urllib.parse.parse_qsl(parsed_url.query)))
    # URLを再構成
    normalized_url = urllib.parse.urlunparse((scheme, netloc, path, parsed_url.params, query, ''))
    
    return normalized_url

# URL内のHTML分を取得
def get_html(url):
    # requestsを使用してWebページのHTMLを取得
    headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }  
    
    response = requests.get(url, headers=headers)
    # BeautifulSoupを使ってHTMLを解析
    soup = BeautifulSoup(response.text, 'html.parser')
    # ページのHTML全体を取得
    html_content = soup.prettify()  # 可読性を向上させたHTMLを取得

    return html_content

# トークン数に基づいてHTMLをトリミングする関数
def trim_html_content(html_content, max_tokens=5000):
    # OpenAIのGPTモデルに対応するトークナイザを取得
    encoding = tiktoken.encoding_for_model("gpt-4")
    
    # HTMLをトークンに変換
    tokenized_html = encoding.encode(html_content)
    
    # トークン数がmax_tokensを超えていない場合、そのまま返す
    if len(tokenized_html) <= max_tokens:
        return html_content
    
    # トークン数がmax_tokensを超えた場合、トリミングする
    trimmed_tokenized_html = tokenized_html[:max_tokens]
    
    # トリミングされたトークンを元のHTML文字列に戻す
    trimmed_html_content = encoding.decode(trimmed_tokenized_html)
    
    return trimmed_html_content

# Show title and description.
st.title("💬 AI Scraping tool")
st.write("")
st.write("LLMを連携させたスクレイピングツールです。")
st.write("ページのHTML構造に関わらず情報を取得させることができます。")
st.write("デモとして、サイト内のページをランダムに5つ取得して、ページ情報を表示します。")
st.write("※同一ページに意図的に連続したアクセスを行う行為はご遠慮ください。")
st.write("")

url = st.text_input("URLを指定してください（例：https://www.rakuten.co.jp/、https://www.amazon.co.jp/）")

if st.button("スクレイピング"):
    links = get_links(url=url)
    # 生成されたコンテンツをリアルタイムで更新
    output_area = st.empty()  # 空の領域を作成して、ここに徐々にテキストを表示する
    if len(links) == 0:
        output_area.write("情報が取得できませんでした") 
    else:
        response = []
        try:
            links = random.sample(links, 5)
            for i in range(5):
                html_contents = get_html(links[i])
                information = get_information(html=html_contents)
                response.append([links[i], information])
                output_area.write(response)  # 現在の内容を表示
        except:
            output_area.write("時間をおいてもう一度試してください")
