import pandas as pd
import numpy as np
import os

# تنظیمات اولیه برای 8760 ساعت
hours = 8760
time_index = pd.date_range(start="2024-01-01", periods=hours, freq="h")

# ==========================================
# 1. تولید پروفایل خودروی برقی (EV)
# ==========================================
# فرض: اوج شارژ بین ساعت 17:00 تا 23:00 است
daily_ev = np.zeros(24)
daily_ev[17:23] = [0.2, 0.6, 0.9, 1.0, 0.8, 0.4] # پیک در ساعت 20:00
daily_ev[0:6] = [0.2, 0.1, 0.1, 0.05, 0.05, 0.05] # ادامه شارژ شبانه

# تکرار برای 365 روز
ev_profile = np.tile(daily_ev, 365)
# اضافه کردن کمی نوسان تصادفی برای واقعی‌تر شدن داده‌ها
ev_profile = ev_profile + np.random.normal(0, 0.05, hours)
ev_profile = np.clip(ev_profile, 0, 1) # نگه داشتن مقادیر بین 0 و 1

# ==========================================
# 2. تولید پروفایل پمپ حرارتی (HP)
# ==========================================
# مصرف HP به فصل بستگی دارد (زمستان اوج مصرف، تابستان حداقل)
day_of_year = time_index.dayofyear
# یک منحنی کسینوسی برای شبیه‌سازی فصل‌ها (اوج در زمستان)
seasonal_factor = (np.cos((day_of_year - 15) * 2 * np.pi / 365) + 1) / 2
seasonal_factor = np.clip(seasonal_factor, 0.1, 1.0) # حداقل 10٪ مصرف در تابستان برای آب گرم

# الگوی مصرف روزانه HP (پیک صبح و عصر)
daily_hp = np.ones(24) * 0.3
daily_hp[6:9] = [0.7, 0.9, 0.6]   # پیک صبحگاهی
daily_hp[17:21] = [0.6, 0.8, 0.9, 0.7] # پیک عصرگاهی

hp_profile = np.tile(daily_hp, 365) * seasonal_factor
hp_profile = hp_profile + np.random.normal(0, 0.05, hours)
hp_profile = np.clip(hp_profile, 0, 1)

# ==========================================
# ذخیره داده‌ها
# ==========================================
df_profiles = pd.DataFrame({
    'EV_Profile_pu': ev_profile,
    'HP_Profile_pu': hp_profile
}, index=time_index)

# اطمینان از وجود پوشه data
os.makedirs('data', exist_ok=True)
df_profiles.to_csv('data/ev_hp_profiles.csv')

# print("✅ پروفایل‌های EV و HP با موفقیت تولید و در 'data/ev_hp_profiles.csv' ذخیره شدند.")
# print("📊 پیش‌نمایش داده‌ها:")
print(df_profiles.head(24)) # نمایش 24 ساعت اول
