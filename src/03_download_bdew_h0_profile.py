import pandas as pd
from demandlib.bdew import ElecSlp

# سال مورد نظر
year = 2023
ann_el_demand = 3500  # kWh سالانه برای یک خانه متوسط

# ساخت پروفایل H0
e_slp = ElecSlp(year)

# استفاده از متد جدید به‌جای get_profile()
profiles = e_slp.get_scaled_power_profiles(
    ann_el_demand_per_sector={"h0": ann_el_demand}
)

# استخراج ستون H0
demand_df = profiles[["h0"]].copy()
demand_df.columns = ["load_kw"]

# ذخیره خروجی
demand_df.to_csv("data/h0_profile_2023.csv")
print(f"Profile saved: {len(demand_df)} timesteps")
print(demand_df.describe())
