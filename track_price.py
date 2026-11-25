import csv
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

# 1. API 키 및 검색·필터·저장 설정
API_KEY = os.environ["SERPAPI_KEY"]
SEARCH_QUERY = "DDR5 16GB"

REQUIRED_WORDS = ["DDR5", "16G"]
EXCLUDE_WORDS = ["중고", "노트북", "8g"]
MIN_PRICE = 50000
MAX_PRICE = 600000
TOP_N = 10

SAVE_DIR = "data"
os.makedirs(SAVE_DIR, exist_ok=True)

TOP_CSV_FILENAME = os.path.join(SAVE_DIR, "prices_top10.csv")
SUMMARY_CSV_FILENAME = os.path.join(SAVE_DIR, "prices_summary.csv")

# 2. SerpApi(구글 쇼핑 한국 기준) 요청
url = "https://serpapi.com/search"
params = {
    "engine": "google_shopping",
    "q": SEARCH_QUERY,
    "gl": "kr",
    "hl": "ko",
    "api_key": API_KEY,
}

response = requests.get(url, params=params, timeout=30)
response.raise_for_status()
data = response.json()
results = data.get("shopping_results", [])

# 3. 필터 통과 상품 선별 및 가격순 정렬
valid_items = []
for item in results:
    title = item.get("title", "")
    price = item.get("extracted_price")
    store = (item.get("source") or "미상").strip()

    if not price:
        continue

    title_upper = title.upper()
    has_required = all(word.upper() in title_upper for word in REQUIRED_WORDS)
    has_excluded = any(word.upper() in title_upper for word in EXCLUDE_WORDS)
    in_price_range = MIN_PRICE <= price <= MAX_PRICE

    if has_required and not has_excluded and in_price_range:
        valid_items.append((price, store, title))

valid_items.sort(key=lambda x: x[0])

# 4. 상위 N개 추출, 평균가 계산 및 CSV 누적 저장
if valid_items:
    top_items = valid_items[:TOP_N]
    sample_count = len(top_items)
    avg_price = round(sum(item[0] for item in top_items) / sample_count)

    lowest_price, lowest_store, lowest_title = top_items[0]
    now_str = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")

    # 4-1. 상위 N개 개별 데이터 저장
    top_file_exists = os.path.isfile(TOP_CSV_FILENAME)
    with open(TOP_CSV_FILENAME, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not top_file_exists:
            writer.writerow(["checked_at", "query", "rank", "price", "store", "title"])
        for rank, (price, store, title) in enumerate(top_items, start=1):
            writer.writerow([now_str, SEARCH_QUERY, rank, int(price), store, title])

    # 4-2. 회차별 최저가 및 평균가 요약 저장
    summary_file_exists = os.path.isfile(SUMMARY_CSV_FILENAME)
    summary_row = [
        now_str,
        SEARCH_QUERY,
        int(lowest_price),
        lowest_store,
        lowest_title,
        avg_price,
        sample_count,
        len(valid_items),
    ]
    with open(SUMMARY_CSV_FILENAME, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not summary_file_exists:
            writer.writerow([
                "checked_at", "query", "lowest_price", "lowest_store",
                "lowest_title", "top_avg_price", "avg_sample_count", "matched_count",
            ])
        writer.writerow(summary_row)

    print(f"기록 완료: 최저가 {int(lowest_price):,}원 / 평균가 {avg_price:,}원 / 통과 {len(valid_items)}개")
else:
    print("조건에 맞는 상품이 없습니다.")
