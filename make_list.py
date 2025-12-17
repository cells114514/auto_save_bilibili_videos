import csv
from pathlib import Path
from get_fav_data import get_bvid_cid_from_fav, count_pages_in_fav
import platform
import portalocker
from threading import Lock

if platform.system() == "Windows":
    from win32com.client import Dispatch    # type: ignore

file_lock = Lock()

def locked_write(path: Path, mode: str, callback):
    with path.open(mode, encoding="utf-8", newline="") as fh:
        portalocker.lock(fh, portalocker.LockFlags.EXCLUSIVE)
        callback(fh)
        fh.flush()
        portalocker.unlock(fh)

def write_lst_to_csv(lst, filename='title_list.csv'):
    output_path = Path(__file__).with_name(filename)
    if not output_path.exists():
        # with output_path.open(mode='w', newline='', encoding='utf-8') as file:
            try:
                def write_header(fh):
                    writer = csv.writer(fh)
                    writer.writerow(['Title', 'BVID', 'CID'])  # 写入表头
                locked_write(output_path, 'w', write_header)
                # writer = csv.writer(file)
                # writer.writerow(['Title', 'BVID', 'CID'])  # 写入表头
                # writer.writerows(lst)  # 写入数据行
                print("title list written successfully.")
            except Exception as e:
                print(f"Error writing to CSV: {e}")
    
    # with output_path.open(mode='a', newline='', encoding='utf-8') as file:
    try:
        def append(fh):
            writer = csv.writer(fh)
            writer.writerows(lst)  # 追加数据行
        with output_path.open('r', encoding='utf-8') as _fh:
            original_lines = sum(1 for _ in _fh)           # 获取原文件行数
        locked_write(output_path, 'a', append)
        with output_path.open('r', encoding='utf-8') as _fh:
            current_lines = sum(1 for _ in _fh)          # 获取当前文件行数
        if current_lines == original_lines:
            print("Warning: No new lines were appended.")
        # elif current_lines > original_lines:
        print("list appended.")
    except Exception as e:
        print(f"Error appending to CSV: {e}")

def load_lst_from_csv(filename='title_list.csv'):
    csv_path = Path(__file__).with_name(filename)
    lst = []
    if not csv_path.exists():
        return lst
    with csv_path.open(mode='r', newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            title = row.get("Title", "")
            bvid = row.get("BVID", "")
            cid = row.get("CID", "")
            lst.append((title, bvid, cid))
    return lst

def find_missing_videos(list=None, media_id=3698183845, csv_filename='title_list.csv'):
    missing_lst = []
    csv_path = Path(__file__).with_name(csv_filename)
    if not csv_path.exists():
        with csv_path.open(mode='w', newline='', encoding='utf-8') as file:
            try:
                print("Creating title list...")
                def write_header(fh):
                    writer = csv.writer(fh)
                    writer.writerow(['Title', 'BVID', 'CID'])  # 写入表头
                locked_write(csv_path, 'w', write_header)
                print("title list written successfully.")
            except Exception as e:
                print(f"Error writing to CSV: {e}")
    lst = get_bvid_cid_from_fav(media_id=media_id, page_num=count_pages_in_fav(media_id=media_id)) if not list else list
    # 有已失效视频列表的时候避免重复请求网页
    # 查找已失效视频完整信息并返回
    for title, bvid, cid in lst:
        if title == "已失效视频":
            with csv_path.open(mode='r', newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    if row["BVID"] == bvid:
                        missing_title = row.get("Title")
                        missing_bvid = row.get("BVID")
                        missing_cid = row.get("cid")
                        missing = (missing_title, missing_bvid, missing_cid)
                        missing_lst.append(missing)
                else:
                    print(f"Missing video: {bvid}")
    return missing_lst

def move_missing_video(missing_lst, txt_filename='已失效视频.txt'):
    txt_path = Path(__file__).with_name(txt_filename)
    video_folder = Path(__file__).with_name("videos")
    def write_missing(fh):
        for title, bvid, cid in missing_lst:
            fh.write(f"{title}\n")
    locked_write(txt_path, "w", write_missing)
    # 移动已失效视频到新的文件夹
    print("Move missing videos to a new folder...\n")
    new_folder = Path(__file__).with_name("已失效视频")
    new_folder.mkdir(exist_ok=True)
    for title, bvid, cid in missing_lst:
        with file_lock:
            video_path = video_folder / f'{title}.mp4'
            if video_path.exists():
                video_path.rename(new_folder / video_path.name)
    print("done.")

def get_media_id(media_id_list):
    # media_id_list = list(map(int, input("getting media id\nPLease input 10-digit media id (split by comma):").split(',')))
    with open(Path(__file__).with_name("media_id.txt"), mode='w', encoding='utf-8') as file:
        for media_id in media_id_list:
            file.write(f"{media_id}\n")
    # return media_id_list

def load_media_id():
    media_id_path = Path(__file__).with_name("media_id.txt")
    if not media_id_path.exists():
        get_media_id([])
        return []
    else:
        with media_id_path.open(mode='r', encoding='utf-8') as file:
            media_id_list = [int(line.strip()) for line in file if line.strip().isdigit()]
        return media_id_list

def make_fav_folder_ink(media_id, title_list):
    # 需要检测当前系统，分别使用不同格式
    os_name = platform.system()
    if os_name == 'windows':
        fav_folder = Path(__file__).with_name(f"fav_{media_id}")
        fav_folder.mkdir(exist_ok=True)
        video_folder = Path(__file__).with_name("videos")
        for title in title_list:
            video_path = video_folder / f'{title}.mp4'
            if video_path.exists():
                with file_lock:
                    target = video_path              # 要创建快捷方式的目标文件
                    shortcut = fav_folder / f"{title}.lnk"   # 快捷方式保存位置
                    shell = Dispatch('WScript.Shell')
                    sc = shell.CreateShortcut(str(shortcut))
                    sc.TargetPath = str(target)
                    sc.WorkingDirectory = str(target.parent)
                    sc.IconLocation = str(target)   # 可选，使用目标文件图标
                    # sc.Description = "视频快捷方式" # 可选描述
                    sc.save()
    elif os_name in ['Linux', 'Darwin']:  # Linux 或 macOS
        fav_folder = Path(__file__).with_name(f"fav_{media_id}")
        fav_folder.mkdir(exist_ok=True)
        video_folder = Path(__file__).with_name("videos")
        for title in title_list:
            video_path = video_folder / f'{title}.mp4'
            if video_path.exists():
                shortcut = fav_folder / f"{title}.desktop"
                with file_lock:
                    with shortcut.open('w', encoding='utf-8') as file:
                        file.write(f"[Desktop Entry]\n")
                        file.write(f"Type=Link\n")
                        file.write(f"Name={title}\n")
                        file.write(f"Icon=video-x-generic\n")
                        file.write(f"URL=file://{video_path.resolve()}\n")
                    shortcut.chmod(0o755)  # 赋予执行权限
    
def load_missing_videos_from_txt(txt_filename='已失效视频.txt'):
    txt_path = Path(__file__).with_name(txt_filename)
    missing_titles = []
    if not txt_path.exists():
        return missing_titles
    with txt_path.open(mode='r', encoding='utf-8') as file:
        for line in file:
            title = line.strip()
            if title:
                missing_titles.append(title)
    return missing_titles