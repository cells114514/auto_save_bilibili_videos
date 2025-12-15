import requests
from lxml import etree # type: ignore
import os

def get_html(url, write_file=True):
    print(f"try getting html from {url}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for HTTP errors
        dir_path = os.path.dirname(__file__)
        print("HTML retrieved successfully.")
        if write_file:
            with open(os.path.join(dir_path, 'output.html'), 'w', encoding='utf-8') as f:
                f.write(response.text)
            print(f"HTML is written.")
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching HTML: {e}")
        return None

def get_cid_list(bvid):
    html = get_html(f"https://www.bilibili.com/video/{bvid}/", write_file=False)
    if not html:
        return [], []
    print("try extracting cid list from html...")
    cid_list = []
    title_list = []
    try:
        tree = etree.HTML(html)
        video_elements = tree.xpath('//div[@data-key]')
        p_title = tree.xpath('//div[@class="title-txt"]/text()')
        for p in p_title:
            if p:
                title_list.append(p)
        for video in video_elements:
            cid = video.get('data-key')
            if cid:
                    cid_list.append(cid)
        print(f"Extracted {len(cid_list)} cids.")
    except Exception as e:
        print(f"Error parsing HTML: {e}")
    return title_list, cid_list

# html = get_html("https://www.bilibili.com/video/BV1d7411v7zu/", write_file=True)
# cids = get_cid_list(html)
# print(cids)