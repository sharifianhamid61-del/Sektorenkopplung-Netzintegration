import pandapower as pp
import pandapower.networks as nw
import pandas as pd
import matplotlib.pyplot as plt
import os

# ==========================================
# 1. Setup Grid & Load Profiles
# ==========================================
print("⚡ Loading CIGRE Low Voltage Network...")
net = nw.create_cigre_network_lv()

print("📊 Loading Profiles...")
profiles = pd.read_csv('data/ev_hp_profiles.csv', index_col=0, parse_dates=True)
winter_day_profiles = profiles.iloc[14*24 : 15*24]

# Add EV (11 kW) and HP (5 kW) loads
residential_buses = net.load.bus.values
for bus in residential_buses:
    pp.create_load(net, bus, p_mw=0.011, q_mvar=0.0, name=f"EV_Bus_{bus}")
    pp.create_load(net, bus, p_mw=0.005, q_mvar=0.001, name=f"HP_Bus_{bus}")

ev_idx = net.load[net.load.name.str.startswith("EV")].index
hp_idx = net.load[net.load.name.str.startswith("HP")].index

# ==========================================
# 2. Run Time-Series H1 (Stress) vs H2 (Controlled)
# ==========================================
res_v_h1, res_load_h1 = [], []
res_v_h2, res_load_h2 = [], []

print("🚀 Running Simulation: H1 (Uncontrolled) vs H2 (§14a EnWG Controlled)...")

for i, (time, row) in enumerate(winter_day_profiles.iterrows()):
    p_ev_uncontrolled = 0.011 * row['EV_Profile_pu']
    p_hp_uncontrolled = 0.005 * row['HP_Profile_pu']
    
    # ------------------ H1: Uncontrolled ------------------
    net.load.loc[ev_idx, 'p_mw'] = p_ev_uncontrolled
    net.load.loc[hp_idx, 'p_mw'] = p_hp_uncontrolled
    
    pp.runpp(net)
    v_min_h1 = net.res_bus.vm_pu.min()
    load_max_h1 = max(net.res_trafo.loading_percent.max(), net.res_line.loading_percent.max())
    
    res_v_h1.append(v_min_h1)
    res_load_h1.append(load_max_h1)
    
    # ------------------ H2: Controlled (§14a EnWG) ------------------
    # Check for Grid Bottlenecks
    if v_min_h1 < 0.9 or load_max_h1 > 100.0:
        print(f"⚠️ Bottleneck detected at hour {i}. Applying §14a Dimming (4.2 kW limit)...")
        # Limit EV power to 4.2 kW (0.0042 MW)
        p_ev_curtailed = min(p_ev_uncontrolled, 0.0042)
        net.load.loc[ev_idx, 'p_mw'] = p_ev_curtailed
        
        # Rerun power flow with curtailed loads
        pp.runpp(net)
        
    res_v_h2.append(net.res_bus.vm_pu.min())
    res_load_h2.append(max(net.res_trafo.loading_percent.max(), net.res_line.loading_percent.max()))

# ==========================================
# 3. Visualization: Compare H1 and H2
# ==========================================
hours = range(24)
plt.figure(figsize=(14, 6))

# Voltage Plot
plt.subplot(1, 2, 1)
plt.plot(hours, res_v_h1, 'r--', linewidth=2, label='H1 (Uncontrolled)')
plt.plot(hours, res_v_h2, 'g-', linewidth=2, marker='o', label='H2 (§14a Controlled)')
plt.axhline(y=0.9, color='black', linestyle=':', label='Limit (0.9 p.u.)')
plt.title("Minimum Grid Voltage")
plt.xlabel("Hour of Day")
plt.ylabel("Voltage (p.u.)")
plt.legend()
plt.grid(True)

# Loading Plot
plt.subplot(1, 2, 2)
plt.plot(hours, res_load_h1, 'r--', linewidth=2, label='H1 (Uncontrolled)')
plt.plot(hours, res_load_h2, 'g-', linewidth=2, marker='s', label='H2 (§14a Controlled)')
plt.axhline(y=100, color='black', linestyle=':', label='Limit (100%)')
plt.title("Max Transformer/Line Loading")
plt.xlabel("Hour of Day")
plt.ylabel("Loading (%)")
plt.legend()
plt.grid(True)

plt.tight_layout()
os.makedirs('outputs', exist_ok=True)
plt.savefig('outputs/H1_vs_H2_Comparison.png', dpi=300)
print("✅ Simulation complete! Comparison plot saved to 'outputs/H1_vs_H2_Comparison.png'.")
plt.show()
