import time
import csv
from pathlib import Path
from typing import Set, List, Tuple

from get_fav_data import get_bvid_cid_from_fav, count_pages_in_fav, PAGE_SIZE
from make_list import write_lst_to_csv, move_missing_video, find_missing_videos  # write_lst_to_csv已集成追加行数功能，可选择替换append_records_to_csv
# 可选：触发下载
from download import down_single_video, down_video_mp4
from make_list import make_fav_folder_ink

CSV_PATH = Path(__file__).with_name("title_list.csv")
MISSING_VIDEO_TXT = Path(__file__).with_name("已失效视频.txt")
MISSING_VIDEO_FOLDER = Path(__file__).with_name("已失效视频")
VIDEO_FOLDER = Path(__file__).with_name("videos")

def init_program():
    # 初始化程序，确保 CSV 文件存在
    if not CSV_PATH.exists():
        with CSV_PATH.open(mode='w', newline='', encoding='utf-8') as file:
            try:
                print("Creating title list...")
                writer = csv.writer(file)
                writer.writerow(['Title', 'BVID', 'CID'])  # 写入表头
                print("title list written successfully.")
            except Exception as e:
                print(f"Error writing to CSV: {e}")
    if not VIDEO_FOLDER.exists():
        VIDEO_FOLDER.mkdir(exist_ok=True)
    if not MISSING_VIDEO_FOLDER.exists():
        MISSING_VIDEO_FOLDER.mkdir(exist_ok=True)
    if not MISSING_VIDEO_TXT.exists():
        MISSING_VIDEO_TXT.touch()
    

def load_known_bvids(csv_path: Path) -> Set[str]:
    if not csv_path.exists():
        return set()
    with csv_path.open(mode='r', newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        bvids = set()
        for row in reader:
            for key in ("bvid", "BVID", "Bvid"):
                if key in row and row[key]:
                    bvids.add(row[key])
                    break
    return bvids

# def append_records_to_csv(records: List[Tuple[str, str, str]], csv_path: Path):
#     file_exists = csv_path.exists()
#     with csv_path.open("a", newline="", encoding="utf-8") as fh:
#         writer = csv.writer(fh)
#         if not file_exists:
#             writer.writerow(["title", "bvid", "cid"])
#         for title, bvid, cid in records:
#             writer.writerow([title, bvid, cid])

def watch_fav(media_id: int, download_new: bool = False, interval: int = 3):
    known = load_known_bvids(CSV_PATH)
    print(f"loaded {len(known)} known bvids")
    # 持续循环逻辑即将改到qtMain，如需无GUI运行，可改为无限循环以持续监控
    # while True:
    try:
        total_pages = count_pages_in_fav(media_id=media_id, page_size=PAGE_SIZE)
        new_list = get_bvid_cid_from_fav(media_id=media_id, page_num=total_pages, page_size=PAGE_SIZE)
        # new_list 是 [(title,bvid,cid), ...]
        added = []
        missing = []
        missing_video_number = 0
        for title, bvid, cid in new_list:
            if title == "已失效视频":
                print("find missing video")
                missing_video_number += 1
                missing.append((title, bvid, cid))
            elif bvid not in known:
                known.add(bvid)
                added.append((title, bvid, cid))
        
        if missing:
                missing = find_missing_videos(list=missing)
                move_missing_video(missing)
                missing_video_number -=1

        if added:
            # 可选：并发或串行下载新增视频
            if download_new:
                print(f"find {len(added)} update.")
                for title, bvid, cid in added:
                    try:
                        down_video_mp4(title, bvid, cid)
                        print(f"trigger download: {title} {bvid} {cid}")
                        make_fav_folder_ink(media_id, [title])  # 为新下载视频创建快捷方式
                    except Exception as e:
                        print(f"download failed {bvid}: {e}")
            else:
                write_lst_to_csv(added)
                print(f"find {len(added)} update, append to {CSV_PATH}")

            
        else:
            print("no new updates")
        time.sleep(interval)
    except Exception as e:
        print(f"Polling error: {e}")
    except KeyboardInterrupt:
        print("Monitoring stopped")
        # break
    
    # print(f"sleeping for {interval} seconds...\n")
    # time.sleep(interval)

if __name__ == "__main__":
    # 简单启动示例：修改 media_id 与间隔（秒）
    try:
        print("welcome.\n please press Ctrl+C to stop monitoring.\n")
        init_program()
        watch_fav(media_id=3698183845, download_new=True, interval=300)
    except KeyboardInterrupt:
        print("Monitoring stopped by user")