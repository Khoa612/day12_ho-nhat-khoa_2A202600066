from langchain_core.tools import tool
import unicodedata

def norm(s: str) -> str:
    """Chuẩn hoá chuỗi thành chữ thường, không dấu, bỏ khoảng trắng."""
    return unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('utf-8').lower().replace(" ", "")

FLIGHTS_DB = {
    ("Hà Nội", "Đà Nẵng"): [
        {"airline": "Vietnam Airlines", "departure": "06:00", "arrival": "07:20", "price": 1_450_000, "class": "economy"},
        {"airline": "Vietnam Airlines", "departure": "14:00", "arrival": "15:20", "price": 2_800_000, "class": "business"},
        {"airline": "VietJet Air", "departure": "08:30", "arrival": "09:50", "price": 890_000, "class": "economy"},
        {"airline": "Bamboo Airways", "departure": "11:00", "arrival": "12:20", "price": 1_200_000, "class": "economy"},
    ],
    ("Hà Nội", "Phú Quốc"): [
        {"airline": "Vietnam Airlines", "departure": "07:00", "arrival": "09:15", "price": 2_100_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "10:00", "arrival": "12:15", "price": 1_350_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "16:00", "arrival": "18:15", "price": 1_100_000, "class": "economy"},
    ],
    ("Hà Nội", "Hồ Chí Minh"): [
        {"airline": "Vietnam Airlines", "departure": "06:00", "arrival": "08:10", "price": 1_600_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "07:30", "arrival": "09:40", "price": 950_000, "class": "economy"},
        {"airline": "Bamboo Airways", "departure": "12:00", "arrival": "14:10", "price": 1_300_000, "class": "economy"},
        {"airline": "Vietnam Airlines", "departure": "18:00", "arrival": "20:10", "price": 3_200_000, "class": "business"},
    ],
    ("Hồ Chí Minh", "Đà Nẵng"): [
        {"airline": "Vietnam Airlines", "departure": "09:00", "arrival": "10:20", "price": 1_300_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "13:00", "arrival": "14:20", "price": 780_000, "class": "economy"},
    ],
    ("Hồ Chí Minh", "Phú Quốc"): [
        {"airline": "Vietnam Airlines", "departure": "08:00", "arrival": "09:00", "price": 1_100_000, "class": "economy"},
        {"airline": "VietJet Air", "departure": "15:00", "arrival": "16:00", "price": 650_000, "class": "economy"},
    ],
}

HOTELS_DB = {
    "Đà Nẵng": [
        {"name": "Mường Thanh Luxury",    "stars": 5, "price_per_night": 1_800_000, "area": "Mỹ Khê",    "rating": 4.5},
        {"name": "Sala Danang Beach",      "stars": 4, "price_per_night": 1_200_000, "area": "Mỹ Khê",    "rating": 4.3},
        {"name": "Fivitel Danang",         "stars": 3, "price_per_night": 650_000,   "area": "Sơn Trà",   "rating": 4.1},
        {"name": "Memory Hostel",          "stars": 2, "price_per_night": 250_000,   "area": "Hải Châu",  "rating": 4.6},
        {"name": "Christina's Homestay",   "stars": 2, "price_per_night": 350_000,   "area": "An Thượng", "rating": 4.7},
    ],
    "Phú Quốc": [
        {"name": "Vinpearl Resort",        "stars": 5, "price_per_night": 3_500_000, "area": "Bãi Dài",    "rating": 4.4},
        {"name": "Sol by Meliá",           "stars": 4, "price_per_night": 1_500_000, "area": "Bãi Trường", "rating": 4.2},
        {"name": "Lahana Resort",          "stars": 3, "price_per_night": 800_000,   "area": "Dương Đông", "rating": 4.0},
        {"name": "9Station Hostel",        "stars": 2, "price_per_night": 200_000,   "area": "Dương Đông", "rating": 4.5},
    ],
    "Hồ Chí Minh": [
        {"name": "Rex Hotel",              "stars": 5, "price_per_night": 2_800_000, "area": "Quận 1",   "rating": 4.3},
        {"name": "Liberty Central",        "stars": 4, "price_per_night": 1_400_000, "area": "Quận 1",   "rating": 4.1},
        {"name": "Cochin Zen Hotel",       "stars": 3, "price_per_night": 550_000,   "area": "Quận 3",   "rating": 4.4},
        {"name": "The Common Room",        "stars": 2, "price_per_night": 180_000,   "area": "Quận 1",   "rating": 4.6},
    ],
}

@tool
def search_flights(origin: str, destination: str) -> str:
    """
    Tìm kiếm các chuyến bay giữa hai thành phố.
    Tham số:
    - origin: thành phố khởi hành (VD: 'Hà Nội', 'Hồ Chí Minh')
    - destination: thành phố đến (VD: 'Đà Nẵng', 'Phú Quốc')
    """
    def find_route(o, d):
        no, nd = norm(o), norm(d)
        for k_o, k_d in FLIGHTS_DB.keys():
            if norm(k_o) == no and norm(k_d) == nd:
                return (k_o, k_d)
        return None

    key = find_route(origin, destination)
    rev_key = find_route(destination, origin)

    def fmt(amount):
        return f"{amount:,}".replace(",", ".")

    if key in FLIGHTS_DB:
        flights = FLIGHTS_DB[key]
        header = f"Danh sách chuyến bay ({origin} -> {destination}):"
    elif rev_key in FLIGHTS_DB:
        flights = FLIGHTS_DB[rev_key]
        header = f"Không tìm thấy chiều {origin} -> {destination}. Gợi ý chiều ngược ({destination} -> {origin}):"
    else:
        return f"Không tìm thấy chuyến bay từ {origin} đến {destination}."

    lines = [header]
    for idx, f in enumerate(flights, 1):
        lines.append(f"{idx}. {f['airline']} | {f['departure']} - {f['arrival']} | Hạng: {f['class']} | Giá: {fmt(f['price'])}đ")
    return "\n".join(lines)

@tool
def search_hotels(city: str, max_price_per_night: int = 99999999) -> str:
    """
    Tìm kiếm khách sạn tại một thành phố, lọc theo giá tối đa mỗi đêm.
    Tham số:
    - city: tên thành phố (VD: 'Đà Nẵng', 'Phú Quốc', 'Hồ Chí Minh')
    - max_price_per_night: giá tối đa mỗi đêm (VNĐ)
    """
    def fmt(amount):
        return f"{amount:,}".replace(",", ".")

    def find_city(c):
        nc = norm(c)
        for k in HOTELS_DB.keys():
            if norm(k) == nc:
                return k
        return None

    actual_city = find_city(city)
    if not actual_city:
        return f"Không có dữ liệu khách sạn tại {city}."

    valid_hotels = [h for h in HOTELS_DB[actual_city] if h["price_per_night"] <= max_price_per_night]
    if not valid_hotels:
        return f"Không tìm thấy khách sạn tại {city} với giá dưới {fmt(max_price_per_night)}đ/đêm."

    valid_hotels.sort(key=lambda x: x["rating"], reverse=True)
    lines = [f"Danh sách khách sạn tại {city} (Giá tối đa: {fmt(max_price_per_night)}đ/đêm):"]
    for idx, h in enumerate(valid_hotels, 1):
        lines.append(f"{idx}. {h['name']} | ★{h['stars']} sao | {h['area']} | Rating: {h['rating']} | {fmt(h['price_per_night'])}đ/đêm")
    return "\n".join(lines)

@tool
def calculate_budget(total_budget: int, expenses: str) -> str:
    """
    Tính toán ngân sách còn lại sau khi trừ các khoản chi phí.
    Tham số:
    - total_budget: tổng ngân sách (VNĐ)
    - expenses: 'tên_khoản:số_tiền,tên_khoản:số_tiền' (VD: 'vé_máy_bay:890000,khách_sạn:650000')
    """
    def fmt(amount):
        return f"{amount:,.0f}".replace(",", ".")

    expenses_dict = {}
    try:
        if expenses.strip():
            for item in expenses.split(","):
                item = item.strip()
                if not item:
                    continue
                if ":" not in item:
                    raise ValueError(f"Thiếu dấu ':' ({item})")
                parts = item.split(":", 1)
                name = parts[0].strip()
                amount_str = parts[1].strip()
                if not amount_str.isdigit():
                    raise ValueError(f"Số tiền không hợp lệ ('{amount_str}')")
                expenses_dict[name] = int(amount_str)
    except Exception as e:
        return f"Lỗi format! Yêu cầu dạng 'tên_khoản:số_tiền,...'. Lỗi: {str(e)}"

    total_expense = sum(expenses_dict.values())
    remaining = total_budget - total_expense

    lines = ["Bảng chi phí:"]
    for name, amount in expenses_dict.items():
        lines.append(f"- {name.capitalize()}: {fmt(amount)}đ")
    lines.append("---")
    lines.append(f"Tổng chi: {fmt(total_expense)}đ")
    lines.append(f"Ngân sách: {fmt(total_budget)}đ")
    lines.append(f"Còn lại: {fmt(remaining)}đ")
    if remaining < 0:
        lines.append(f"⚠️ Vượt ngân sách {fmt(abs(remaining))}đ!")
    return "\n".join(lines)
