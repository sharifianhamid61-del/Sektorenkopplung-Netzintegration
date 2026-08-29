import pandapower as pp
import pandapower.networks as nw
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def run_decoupled_analysis():
    print("Initializing CIGRE Low Voltage Network...")
    net = nw.create_cigre_network_lv()
    
    # تعریف 24 ساعت (یک روز بحرانی فرضی)
    hours = np.arange(24)
    
    # پروفایل‌های فرضی نرمال‌شده (بین 0 تا 1) برای 24 ساعت
    # بار پایه: پیک در ظهر و اوایل شب
    base_profile = np.array([0.3, 0.25, 0.2, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.65, 
                             0.6, 0.55, 0.5, 0.5, 0.5, 0.6, 0.7, 0.85, 0.9, 0.8, 
                             0.7, 0.6, 0.5, 0.4])
    
    # پروفایل پمپ حرارتی (HP): توان 4 کیلووات، فعال در صبح زود و عصر/شب
    hp_kw = 4.0 / 1000  # تبدیل به مگاوات
    hp_profile = np.array([0.5, 0.5, 0.6, 0.7, 0.8, 0.9, 0.8, 0.6, 0.4, 0.2, 
                           0.2, 0.2, 0.2, 0.3, 0.4, 0.6, 0.8, 0.9, 1.0, 0.9, 
                           0.8, 0.7, 0.6, 0.5])
    
    # پروفایل خودرو الکتریکی (EV): توان 11 کیلووات، شارژ عمدتاً بعد از کار (17:00 به بعد)
    ev_kw = 11.0 / 1000 # تبدیل به مگاوات
    ev_profile = np.array([0.1, 0.1, 0.0, 0.0, 0.0, 0.0, 0.1, 0.2, 0.1, 0.0, 
                           0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.3, 0.7, 1.0, 0.9, 
                           0.7, 0.4, 0.2, 0.1])

    # توان اکتیو اولیه بارهای شبکه
    base_p_mw = net.load.p_mw.values.copy()
    
    # دیکشنری برای ذخیره حداقل ولتاژ در هر ساعت برای 4 سناریو
    results = {
        'Base Load': [],
        'Base + HP': [],
        'Base + EV': [],
        'Base + HP + EV (H1)': []
    }

    print("Running Power Flow for 24 hours across 4 scenarios...")

    for h in hours:
        # سناریو 1: فقط بار پایه
        net.load.p_mw = base_p_mw * base_profile[h]
        pp.runpp(net)
        results['Base Load'].append(net.res_bus.vm_pu.min())

        # سناریو 2: بار پایه + پمپ حرارتی
        net.load.p_mw = (base_p_mw * base_profile[h]) + (hp_kw * hp_profile[h])
        pp.runpp(net)
        results['Base + HP'].append(net.res_bus.vm_pu.min())

        # سناریو 3: بار پایه + خودرو الکتریکی
        net.load.p_mw = (base_p_mw * base_profile[h]) + (ev_kw * ev_profile[h])
        pp.runpp(net)
        results['Base + EV'].append(net.res_bus.vm_pu.min())

        # سناریو 4: بار پایه + پمپ حرارتی + خودرو الکتریکی (بدترین حالت)
        net.load.p_mw = (base_p_mw * base_profile[h]) + (hp_kw * hp_profile[h]) + (ev_kw * ev_profile[h])
        pp.runpp(net)
        results['Base + HP + EV (H1)'].append(net.res_bus.vm_pu.min())

    # --- مصورسازی و رسم نمودار تحلیلی ---
    print("Generating Decoupled Analysis Chart...")
    plt.figure(figsize=(12, 6))
    plt.style.use('seaborn-v0_8-darkgrid')
    
    # رسم خطوط
    plt.plot(hours, results['Base Load'], label='1. Base Load Only', color='green', linewidth=2.5, linestyle='--')
    plt.plot(hours, results['Base + HP'], label='2. Base + Heat Pumps (4 kW)', color='blue', linewidth=2.5)
    plt.plot(hours, results['Base + EV'], label='3. Base + EVs (11 kW)', color='orange', linewidth=2.5)
    plt.plot(hours, results['Base + HP + EV (H1)'], label='4. Full Sektorenkopplung (Uncontrolled)', color='red', linewidth=3)
    
    # خط حد مجاز ولتاژ
    plt.axhline(y=0.85, color='black', linestyle=':', linewidth=2, label='Critical Voltage Limit (0.85 p.u.)')

    # تنظیمات گرافیکی
    plt.title('Decoupled Impact of EVs and Heat Pumps on Grid Voltage (24h Worst-Case)', fontsize=14, fontweight='bold')
    plt.xlabel('Hour of the Day', fontsize=12)
    plt.ylabel('Minimum Grid Voltage (p.u.)', fontsize=12)
    plt.xticks(hours)
    plt.ylim(0.80, 1.02)
    plt.legend(loc='lower left', fontsize=10, frameon=True, shadow=True)
    
    # هایلایت کردن نقطه بحرانی
    min_vol_h1 = min(results['Base + HP + EV (H1)'])
    min_hour = results['Base + HP + EV (H1)'].index(min_vol_h1)
    plt.annotate(f'Voltage Collapse!\n{min_vol_h1:.2f} p.u.', 
                 xy=(min_hour, min_vol_h1), xytext=(min_hour-3, min_vol_h1-0.03),
                 arrowprops=dict(facecolor='red', shrink=0.05),
                 color='red', fontweight='bold')

    plt.tight_layout()
    plt.savefig('EV_vs_HP_Impact.png', dpi=300)
    plt.show()
    print("Done! Chart saved as 'EV_vs_HP_Impact.png'")

if __name__ == "__main__":
    run_decoupled_analysis()
