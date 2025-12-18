import requests
from pathlib import Path
import tqdm
from get_fav_data import get_json, PAGE_SIZE, get_bvid_cid_from_fav, count_pages_in_fav
from get_p_cid import get_cid_list
from make_list import write_lst_to_csv
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import math
# ...existing code...

def down_video_mp4(title, bvid, cid, session=None, qn=32, write_json=False):       # 下载MP4视频
    new_folder = Path(__file__).with_name("videos")
    new_folder.mkdir(exist_ok=True)
    final_path = new_folder / f'{title}.mp4'
    if final_path.exists():
        print(f"File already exists: {final_path}")
        return
    
    # 延迟获取默认 session，避免循环导入问题
    if session is None:
        try:
            from get_fav_data import mysession as default_session
            session = default_session
        except Exception:
            session = requests.Session()

    # 强化 session：连接池和重试
    try:
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500,502,503,504])
        adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
    except Exception:
        pass

    session.headers.update({'Referer': f'https://www.bilibili.com/video/{bvid}'})
    print(f"downloading {title}...")

    video_api = f"https://api.bilibili.com/x/player/wbi/playurl?cid={cid}&bvid={bvid}&gaia_source=view-card&qn={qn}"
    video_json = get_json(video_api, name=f'video_{bvid}_{cid}', write_file=write_json)
    if not video_json:
        print("no video json")
        return

    durls = video_json['data'].get('durl', [])
    if not durls:
        print("no download urls")
        return

    # 如果只有一个分段，尝试使用 Range 并行下载（若服务器支持）
    chunk_size = 65536
    if len(durls) == 1:
        url = durls[0]['url']

        def _head_info(u):
            try:
                h = session.head(u, allow_redirects=True, timeout=15)
                h.raise_for_status()
                return h.headers
            except Exception:
                return {}

        headers = _head_info(url)
        total = int(headers.get('Content-Length') or 0)
        accept_ranges = headers.get('Accept-Ranges', '').lower() == 'bytes'

        # 并行分片下载的阈值与并发数
        MIN_PARALLEL_SIZE = 2 * 1024 * 1024  # 文件至少大于 2MB 才并行
        MAX_WORKERS = 4

        if accept_ranges and total >= MIN_PARALLEL_SIZE:
            # 计算分片区间
            part_count = min(MAX_WORKERS, math.ceil(total / (4 * 1024 * 1024)))  # 每片约 4MB
            part_size = math.ceil(total / part_count)
            tmp_dir = Path(tempfile.mkdtemp())
            part_paths = []

            def download_range(idx, start, end, out_path):
                hdr = {'Range': f'bytes={start}-{end}', 'Referer': session.headers.get('Referer', '')}
                with session.get(url, headers=hdr, stream=True, timeout=30) as r:
                    r.raise_for_status()
                    with out_path.open('wb') as f:
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)
                return out_path

            try:
                with ThreadPoolExecutor(max_workers=part_count) as ex:
                    futures = []
                    for i in range(part_count):
                        start = i * part_size
                        end = min(total - 1, (i + 1) * part_size - 1)
                        part_file = tmp_dir / f'part_{i}.tmp'
                        part_paths.append(part_file)
                        futures.append(ex.submit(download_range, i, start, end, part_file))

                    for fut in as_completed(futures):
                        fut.result()  # 若抛异常会在这里暴露并中断

                # 合并
                with final_path.open('wb') as outfile:
                    for part_file in part_paths:
                        with part_file.open('rb') as pf:
                            shutil.copyfileobj(pf, outfile)

                write_lst_to_csv([(title, bvid, cid)])
                print(f"Downloaded (parallel ranges): {final_path}")

            finally:
                try:
                    shutil.rmtree(tmp_dir)
                except Exception:
                    pass

            return

        # 回退：单连接顺序下载（增大块）
        with session.get(url, stream=True, timeout=30) as resp:
            try:
                resp.raise_for_status()
            except requests.RequestException as e:
                print(f"Error while downloading the video: {e}")
                return
            total = total or int(resp.headers.get('Content-Length', 0))
            with final_path.open("wb") as fh, tqdm.tqdm(total=total, unit='B', unit_scale=True, desc=title, leave=True) as pbar:
                for chunk in resp.iter_content(chunk_size=chunk_size):
                    if chunk:
                        fh.write(chunk)
                        pbar.update(len(chunk))
        write_lst_to_csv([(title, bvid, cid)])
        print(f"Downloaded: {final_path}")
        return

# 以下是提供的多分段下载，平常更新收藏夹无需用到，仅供参考
# 合集的data-key字段为bvid，略微修改即可，课程视频的data-key字段是cid（此处的实现）

def get_cid_with_bvid(bvid):
    url = f"https://api.bilibili.com/x/player/pagelist?bvid={bvid}&amp;jsonp=jsonp​"
    json = get_json(url, write_file=False)
    if json:
        cid = json['data'][0]['cid']
        return cid
    return None

def get_and_write_video_list(media_id, write_file=False):
    lst = get_bvid_cid_from_fav(media_id=media_id, page_num=count_pages_in_fav(media_id=3698183845))
    if write_file:
        write_lst_to_csv(lst, filename='title_list.csv')
    return lst

def down_video_with_parts(total_name, total_bvid, total_cid, start_p=1,end_p=None):     # 下载多分段视频
    title, cids = get_cid_list(total_bvid)
    if cids:
        for index, cid in enumerate(cids):
            if start_p <= index + 1 <= (end_p if end_p is not None else float('inf')):
                print(f"downloading part {index + 1} with cid {cid}...")
                down_video_mp4(title[index], total_bvid, cid)
    # elif bvids:           #实际上合集里面的视频是单独存在的，每个视频都有单独的bvid，不需要整个合集一起下载时，只需要在在收藏夹里面单独收藏即可
    #     for index, bvid in enumerate(bvids):
    #         cid = get_cid_with_bvid(bvid)
    #         if cid:
    #             if start_p <= index + 1 <= (end_p if end_p is not None else float('inf')):
    #                 print(f"downloading part {index + 1} with cid {cid}...")
    #                 down_video_mp4(f"{cid}_{index + 1}", bvid, cid)
    else:
        down_video_mp4(total_name, total_bvid, total_cid)
         
def down_videos_from_list():
    lst = get_and_write_video_list(3698183845, write_file=False)
    for title, bvid, cid in lst:
        down_video_with_parts(title, bvid, cid)

def down_single_video(title, bvid, cid=None):    #提供了不知道cid的下载方法
    if not cid:
        cid = get_cid_with_bvid(bvid)
        down_video_mp4(title, bvid, cid)
    else:
        down_video_mp4(title, bvid, cid)

# if __name__ == "__main__":
#     down_videos_from_list()