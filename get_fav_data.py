import requests
import json
from pathlib import Path


mysession = requests.Session()
mysession.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
})

PAGE_SIZE = 20  # 每页项目数


def get_json(url, name='default', write_file=True):     # 从api取出json
    try:
        response = mysession.get(url, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses
    except requests.RequestException as e:
        print(f"Error fetching the URL: {e}")
        return None

    if write_file:
        output_path = Path(__file__).with_name(f'{name}.json')
        with output_path.open('w', encoding='utf-8') as file:
            json.dump(response.json(), file, ensure_ascii=False, indent=4)
    return response.json()

def get_bvid_cid_from_fav(media_id, page_num, page_size=PAGE_SIZE):   # 从收藏夹获取bvid和cid
    print(f"try getting bvid and cid from fav page {page_num}...")
    bvid_cid_list = []
    for page in range(1, page_num+1):
        url = f"https://api.bilibili.com/x/v3/fav/resource/list?media_id={media_id}&ps={page_size}&pn={page}"
        json_data = get_json(url, name=f'fav_list_3698183845_page_{page}', write_file=False)

        if not json_data or 'data' not in json_data or 'medias' not in json_data['data']:
            print("Invalid JSON data")
            return []

        for item in json_data['data']['medias']:
            title = item.get('title')
            bvid = item.get('bvid')
            ugc = item.get('ugc')
            cid = ugc.get('first_cid') if ugc else None
            if title and bvid and cid:
                bvid_cid_list.append((title, bvid, cid))
                print(f"Found video - Title: {title}, BVID: {bvid}, CID: {cid}")
    print("done.")
    return bvid_cid_list


def count_pages_in_fav(media_id, page_size=PAGE_SIZE):      # 数页数
    print("try counting pages in fav...")
    url = f"https://api.bilibili.com/x/v3/fav/resource/list?media_id={media_id}&ps={page_size}&pn=1"
    json_data = get_json(url, name='fav_list_count', write_file=False)

    if not json_data or 'data' not in json_data or 'info' not in json_data['data']:
        print("Invalid JSON data")
        return 0

    total_count = json_data['data']['info'].get('media_count', 0)
    total_pages = (total_count + page_size - 1) // page_size
    print(f"find {total_pages} pages.")
    return total_pages


# 批量下载收藏夹视频
# lst = get_bvid_cid_from_fav(media_id=3698183845, page_num=count_pages_in_fav(media_id=3698183845))
# write_lst_to_csv(lst, filename='title_list.csv')
# for title, bvid, cid in lst:
#     down_video_mp4(title, bvid, cid, qn=32, write_json=False)

# session.headers.update({
#     'Referer': 'https://www.bilibili.com/video/BV1F9xMz6Ecp'
# })
# get_json('https://api.bilibili.com/x/player/wbi/playurl?cid=144238503&bvid=BV1d7411v7zu&gaia_source=view-card&qn=32', name='video', write_file=True)







# 3698183845测试收藏夹id
# 视频api：https://api.bilibili.com/x/player/wbi/playurl

# bvid = 'BV1F9xMz6Ecp'
# cid = '32857067434'
# down_video_mp4(bvid, cid, qn=32)
