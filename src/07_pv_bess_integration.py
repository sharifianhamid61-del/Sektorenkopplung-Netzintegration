import pandapower as pp
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==========================================
# 1. Network Setup (Aggregated 10 Prosumers)
# ==========================================
def create_base_network():
    net = pp.create_empty_network()
    # Buses
    b_ext = pp.create_bus(net, vn_kv=20., name="MV Grid")
    b_trafo = pp.create_bus(net, vn_kv=0.4, name="LV Trafo")
    b_prosumers = pp.create_bus(net, vn_kv=0.4, name="Prosumers Aggregated")
    
    # Grid & Trafo (160 kVA to show loading effects clearly)
    pp.create_ext_grid(net, b_ext, s_sc_max_mva=100)
    pp.create_transformer(net, b_ext, b_trafo, std_type="0.25 MVA 20/0.4 kV")
  
    # Line (800m NAYY 4x150)
    pp.create_line(net, b_trafo, b_prosumers, length_km=0.8, std_type="NAYY 4x150 SE")
    
    # Elements (Initial states, will be updated in TS loop)
    pp.create_load(net, b_prosumers, p_mw=0.0, name="Aggregated Load")
    pp.create_sgen(net, b_prosumers, p_mw=0.0, type="pv", name="Aggregated PV")
    # Storage (10 houses * 10 kWh = 100 kWh total)
    pp.create_storage(net, b_prosumers, p_mw=0.0, max_e_mwh=0.1, name="Aggregated BESS")
    
    return net

# ==========================================
# 2. 24-Hour Profiles (in kW for 10 Houses)
# ==========================================
hours = np.arange(24)
houses_count = 10

# Load Profiles
base_load = np.ones(24) * 1.0 * houses_count  # 1 kW per house base
ev_load = np.zeros(24)
ev_load[17:22] = 11.0 * houses_count         # 11 kW EV charging (17:00-22:00)
hp_load = np.zeros(24)
hp_load[16:23] = 3.0 * houses_count          # 3 kW HP (16:00-23:00)
total_load = base_load + ev_load + hp_load

# PV Profile (Bell curve, peak at 13:00, 8 kW per house max)
pv_gen = np.zeros(24)
pv_gen[7:19] = (8.0 * houses_count) * np.sin(np.pi * np.arange(12) / 11)

# ==========================================
# 3. Time Series Simulation Function
# ==========================================
def run_24h_simulation(use_bess=False):
    net = create_base_network()
    
    # BESS Parameters for the aggregated node
    bess_capacity_kwh = 100.0  # 10 houses * 10 kWh
    max_p_bess_kw = 40.0       # 10 houses * 4 kW max charge/discharge
    soc_kwh = 20.0             # Start with 20% SoC
    
    # Result arrays
    v_bus_pu = []
    trafo_loading = []
    grid_exchange_kw = []
    bess_p_array = []
    
    for t in range(24):
        p_load_t = total_load[t]
        p_pv_t = pv_gen[t]
        p_bess_t = 0.0 # Default: idle
        
        if use_bess:
            # HEMS Logic: Net Load
            p_net = p_load_t - p_pv_t
            
            if p_net < 0: # PV Surplus -> Charge Battery
                charge_needed = -p_net
                charge_actual = min(charge_needed, max_p_bess_kw, (bess_capacity_kwh - soc_kwh))
                p_bess_t = -charge_actual # In pandapower, negative means charging (consuming)
                soc_kwh += charge_actual
                
            elif p_net > 0: # Energy Deficit -> Discharge Battery
                discharge_needed = p_net
                discharge_actual = min(discharge_needed, max_p_bess_kw, soc_kwh)
                p_bess_t = discharge_actual # Positive means discharging (generating)
                soc_kwh -= discharge_actual
        
        # Update Network Elements (convert kW to MW)
        net.load.p_mw[0] = p_load_t / 1000.0
        net.sgen.p_mw[0] = p_pv_t / 1000.0
        net.storage.p_mw[0] = p_bess_t / 1000.0
        
        # Run Load Flow
        pp.runpp(net)
        
        # Record Results
        v_bus_pu.append(net.res_bus.vm_pu.at[2]) # Voltage at Prosumers bus
        trafo_loading.append(net.res_trafo.loading_percent.at[0])
        # Grid exchange = Net power drawn from external grid (+ is drawing, - is feeding back)
        grid_exchange_kw.append(net.res_ext_grid.p_mw.at[0] * 1000.0) 
        bess_p_array.append(p_bess_t)

    return v_bus_pu, trafo_loading, grid_exchange_kw, bess_p_array

# ==========================================
# 4. Run Scenarios & Plot
# ==========================================
print("Running Scenario 1: PV Only (No Battery)...")
v_pv, t_pv, g_pv, _ = run_24h_simulation(use_bess=False)

print("Running Scenario 2: PV + BESS (Smart HEMS)...")
v_bess, t_bess, g_bess, bess_power = run_24h_simulation(use_bess=True)

# Plotting Results
plt.style.use('seaborn-v0_8-darkgrid')
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 14), sharex=True)

# --- Subplot 1: Power Profiles (PV+BESS Scenario) ---
ax1.plot(hours, total_load, label="Total Load (EV+HP+Base)", color='red', lw=2)
ax1.plot(hours, pv_gen, label="PV Generation", color='orange', lw=2, linestyle='--')
ax1.bar(hours, bess_power, label="BESS Power (+Discharge / -Charge)", color='purple', alpha=0.5)
ax1.set_ylabel("Power (kW)", fontweight='bold')
ax1.set_title("24-Hour Power Profiles (10 Aggregated Prosumers) with BESS", fontweight='bold', fontsize=12)
ax1.legend(loc="upper left")

# --- Subplot 2: Voltage Profile ---
ax2.plot(hours, v_pv, label="S1: PV Only (No Battery)", color='red', lw=2, marker='o')
ax2.plot(hours, v_bess, label="S2: PV + BESS (HEMS)", color='green', lw=2, marker='s')
ax2.axhline(1.05, color='black', linestyle=':', label="Upper Limit (1.05 pu)")
ax2.axhline(0.85, color='black', linestyle=':', label="Lower Limit (0.85 pu)")
ax2.set_ylabel("Voltage (p.u.)", fontweight='bold')
ax2.set_title("Voltage Profile at End of Feeder", fontweight='bold', fontsize=12)
ax2.legend(loc="best")

# --- Subplot 3: Transformer Loading ---
ax3.plot(hours, t_pv, label="S1: PV Only Loading", color='red', lw=2, marker='o')
ax3.plot(hours, t_bess, label="S2: PV + BESS Loading", color='green', lw=2, marker='s')
ax3.axhline(100, color='black', linestyle=':', label="Trafo Limit (100%)")
ax3.set_ylabel("Loading (%)", fontweight='bold')
ax3.set_xlabel("Hour of Day", fontweight='bold')
ax3.set_title("Transformer Loading Profile", fontweight='bold', fontsize=12)
ax3.set_xticks(hours)
ax3.legend(loc="best")

plt.tight_layout()
plt.savefig("PV_BESS_Integration.png", dpi=300)
print("Simulation complete! Results saved to 'PV_BESS_Integration.png'")
plt.show()
