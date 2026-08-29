import pandapower as pp
import pandapower.networks as nw
import pandas as pd
import matplotlib.pyplot as plt
import os

# ==========================================
# 1. Load Base Grid (H0) & Profiles
# ==========================================
print("⚡ Loading CIGRE Low Voltage Network...")
net = nw.create_cigre_network_lv()

print("📊 Loading EV & HP Profiles...")
profiles = pd.read_csv('data/ev_hp_profiles.csv', index_col=0, parse_dates=True)

# انتخاب یک روز سرد زمستانی (مثلاً 15 ژانویه)
winter_day_profiles = profiles.iloc[14*24 : 15*24]

# ==========================================
# 2. Setup Stress Case H1 (Uncontrolled EV & HP)
# ==========================================
residential_buses = net.load.bus.values

for bus in residential_buses:
    # EV: 11 kW = 0.011 MW | HP: 5 kW = 0.005 MW
    pp.create_load(net, bus, p_mw=0.011, q_mvar=0.0, name=f"EV_Bus_{bus}")
    pp.create_load(net, bus, p_mw=0.005, q_mvar=0.001, name=f"HP_Bus_{bus}")

ev_indices = net.load[net.load.name.str.startswith("EV")].index
hp_indices = net.load[net.load.name.str.startswith("HP")].index

# ==========================================
# 3. Run Time-Series Simulation (24h)
# ==========================================
results_v_min = []
results_loading_max = []

print("🚀 Running Stress Case H1 (Uncontrolled) Simulation for 24h...")

for i, (time, row) in enumerate(winter_day_profiles.iterrows()):
    net.load.loc[ev_indices, 'p_mw'] = 0.011 * row['EV_Profile_pu']
    net.load.loc[hp_indices, 'p_mw'] = 0.005 * row['HP_Profile_pu']
    
    try:
        pp.runpp(net)
        results_v_min.append(net.res_bus.vm_pu.min())
        results_loading_max.append(max(net.res_trafo.loading_percent.max(), net.res_line.loading_percent.max()))
    except pp.LoadflowNotConverged:
        print(f"❌ Non-convergence at hour {i} - Grid collapse!")
        results_v_min.append(float('nan'))
        results_loading_max.append(float('nan'))

# ==========================================
# 4. Visualization (H1 Results)
# ==========================================
hours = range(24)
plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.plot(hours, results_v_min, color='red', marker='o', linewidth=2, label='Min Voltage (H1)')
plt.axhline(y=0.9, color='black', linestyle='--', label='Limit (0.9 p.u.)')
plt.title("Stress Case H1: Minimum Grid Voltage")
plt.xlabel("Hour of Day")
plt.ylabel("Voltage (p.u.)")
plt.legend()
plt.grid(True)

plt.subplot(1, 2, 2)
plt.plot(hours, results_loading_max, color='blue', marker='s', linewidth=2, label='Max Loading (H1)')
plt.axhline(y=100, color='black', linestyle='--', label='Limit (100%)')
plt.title("Stress Case H1: Transformer/Line Loading")
plt.xlabel("Hour of Day")
plt.ylabel("Loading (%)")
plt.legend()
plt.grid(True)

plt.tight_layout()
os.makedirs('outputs', exist_ok=True)
plt.savefig('outputs/H1_stress_test_results.png', dpi=300)
print("✅ H1 Simulation complete! Plot saved to 'outputs/H1_stress_test_results.png'.")
plt.show()
