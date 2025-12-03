import argparse
from utils.webpage_crawler import WebpageCrawler

def main():
    p = argparse.ArgumentParser()
    p.add_argument("urls", nargs="+", help="要爬取的网页 URL 列表")
    p.add_argument("--data-dir", default="data")
    args = p.parse_args()
    wc = WebpageCrawler(data_dir=args.data_dir)
    for u in args.urls:
        try:
            res = wc.crawl_and_parse(u, save_data=True)
            print({"url": u, "files": res.get("file_paths")})
        except Exception as e:
            print({"url": u, "error": str(e)})

if __name__ == "__main__":
    main()