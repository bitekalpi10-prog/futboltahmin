"""Haftalık bülteni bir defa yenilemek için: python refresh.py"""
from app import build_weekly_bulletin
data = build_weekly_bulletin()
print(f"Bülten üretildi: {len(data.get('matches', []))} maç; {data.get('generated_at')}")
if data.get("errors"):
    print("Uyarılar:")
    for error in data["errors"]:
        print("-", error)
