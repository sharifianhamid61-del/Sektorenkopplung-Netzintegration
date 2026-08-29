import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import pandapower as pp
import pandapower.networks as nw

from pandapower.timeseries import DFData
from pandapower.timeseries import OutputWriter
from pandapower.timeseries.run_time_series import run_timeseries
from pandapower.control import ConstControl


# ============================================================
# 1. CREATE PROFILES
# ============================================================

def create_profiles():
    """
    ایجاد پروفایل‌های 24 ساعته با رزولوشن 15 دقیقه‌ای
    """

    steps = 96
    t = np.linspace(0, 24, steps, endpoint=False)

    # --------------------------------------------------------
    # Household Load Profile
    # --------------------------------------------------------

    household = (
        0.35
        + 0.20 * np.sin((t - 6) * np.pi / 12)
        + 0.55 * np.exp(-((t - 19) ** 2) / 4)
    )

    household = np.clip(
        household,
        0.2,
        1.3
    )

    # --------------------------------------------------------
    # EV Charging Profile
    # Charging mainly from 18:00 to 06:00
    # --------------------------------------------------------

    ev = np.where(
        (t >= 18) | (t < 6),
        1.0,
        0.0
    )

    # --------------------------------------------------------
    # Heat Pump Profile
    # Higher demand during evening hours
    # --------------------------------------------------------

    hp = np.where(
        (t >= 17) & (t <= 22),
        1.0,
        0.4
    )

    # --------------------------------------------------------
    # Evening Peak Indicator
    # --------------------------------------------------------

    evening_peak = np.where(
        (t >= 17) & (t <= 22),
        1.0,
        0.0
    )

    profiles = pd.DataFrame({
        "household": household,
        "ev": ev,
        "hp": hp,
        "evening_peak": evening_peak
    })

    return profiles


# ============================================================
# 2. ADD MULTIPLE EVS
# ============================================================

def add_evs(net):
    """
    اضافه کردن چند شارژر EV
    """

    ev_buses = [5, 8, 10, 12, 15]

    for i, bus in enumerate(ev_buses):

        pp.create_load(
            net,
            bus=bus,
            p_mw=0.011,
            q_mvar=0.0,
            scaling=1.0,
            name=f"EV_{i + 1}"
        )

    print(f"{len(ev_buses)} EV chargers added.")


# ============================================================
# 3. ADD HEAT PUMPS
# ============================================================

def add_heat_pumps(net):
    """
    اضافه کردن Heat Pump
    """

    hp_buses = [6, 9, 11, 14]

    for i, bus in enumerate(hp_buses):

        pp.create_load(
            net,
            bus=bus,
            p_mw=0.005,
            q_mvar=0.0,
            scaling=1.0,
            name=f"HP_{i + 1}"
        )

    print(f"{len(hp_buses)} Heat Pumps added.")


# ============================================================
# 4. SETUP CONTROLLERS
# ============================================================

def setup_controllers(net, profiles):
    """
    اتصال پروفایل‌ها به بارهای شبکه
    """

    ds = DFData(profiles)

    # --------------------------------------------------------
    # Household Loads
    # --------------------------------------------------------

    household_loads = net.load[
        ~net.load["name"].astype(str).str.startswith(
            ("EV_", "HP_")
        )
    ].index

    if len(household_loads) > 0:

        ConstControl(
            net,
            element="load",
            variable="scaling",
            element_index=household_loads,
            data_source=ds,
            profile_name="household"
        )

    # --------------------------------------------------------
    # EV Loads
    # --------------------------------------------------------

    ev_loads = net.load[
        net.load["name"].astype(str).str.startswith("EV_")
    ].index

    if len(ev_loads) > 0:

        ConstControl(
            net,
            element="load",
            variable="scaling",
            element_index=ev_loads,
            data_source=ds,
            profile_name="ev"
        )

    # --------------------------------------------------------
    # Heat Pump Loads
    # --------------------------------------------------------

    hp_loads = net.load[
        net.load["name"].astype(str).str.startswith("HP_")
    ].index

    if len(hp_loads) > 0:

        ConstControl(
            net,
            element="load",
            variable="scaling",
            element_index=hp_loads,
            data_source=ds,
            profile_name="hp"
        )


# ============================================================
# 5. CREATE OUTPUT WRITER
# ============================================================

def create_output_writer(net):
    """
    ذخیره نتایج Time Series
    """

    output_dir = os.path.join(
        os.getcwd(),
        "outputs",
        "evening_peak"
    )

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    ow = OutputWriter(
        net,
        output_path=output_dir,
        output_file_type=".json"
    )

    # Voltage results
    ow.log_variable(
        "res_bus",
        "vm_pu"
    )

    # Line loading results
    ow.log_variable(
        "res_line",
        "loading_percent"
    )

    return output_dir


# ============================================================
# 6. PLOT RESULTS
# ============================================================

def plot_results(profiles, vm_pu, loading, output_dir):
    """
    رسم نمودارهای سناریوی Evening Peak
    """

    time_hours = np.arange(96) * 0.25

    # --------------------------------------------------------
    # Network Indicators
    # --------------------------------------------------------

    min_voltage = vm_pu.min(axis=1)

    max_loading = loading.max(axis=1)

    # --------------------------------------------------------
    # Create Figure
    # --------------------------------------------------------

    plt.figure(figsize=(12, 14))

    # ========================================================
    # PLOT 1 - LOAD PROFILES
    # ========================================================

    plt.subplot(3, 1, 1)

    plt.plot(
        time_hours,
        profiles["household"],
        label="Household Load Profile",
        linewidth=2
    )

    plt.plot(
        time_hours,
        profiles["ev"],
        label="EV Charging Profile",
        linewidth=2
    )

    plt.plot(
        time_hours,
        profiles["hp"],
        label="Heat Pump Profile",
        linewidth=2
    )

    plt.axvspan(
        17,
        22,
        alpha=0.2,
        label="Evening Peak Period"
    )

    plt.title(
        "Load Profiles and Evening Peak Scenario"
    )

    plt.xlabel(
        "Time (Hour)"
    )

    plt.ylabel(
        "Scaling Factor"
    )

    plt.xlim(0, 24)

    plt.grid(True)

    plt.legend()

    # ========================================================
    # PLOT 2 - MINIMUM NETWORK VOLTAGE
    # ========================================================

    plt.subplot(3, 1, 2)

    plt.plot(
        time_hours,
        min_voltage,
        label="Minimum Network Voltage",
        linewidth=2
    )

    plt.axhline(
        0.90,
        linestyle="--",
        label="Voltage Limit (0.90 pu)"
    )

    plt.axvspan(
        17,
        22,
        alpha=0.2,
        label="Evening Peak Period"
    )

    plt.title(
        "Minimum Voltage in the Network"
    )

    plt.xlabel(
        "Time (Hour)"
    )

    plt.ylabel(
        "Voltage (p.u.)"
    )

    plt.xlim(0, 24)

    plt.grid(True)

    plt.legend()

    # ========================================================
    # PLOT 3 - MAXIMUM LINE LOADING
    # ========================================================

    plt.subplot(3, 1, 3)

    plt.plot(
        time_hours,
        max_loading,
        label="Maximum Line Loading",
        linewidth=2
    )

    plt.axhline(
        100,
        linestyle="--",
        label="Line Loading Limit (100%)"
    )

    plt.axvspan(
        17,
        22,
        alpha=0.2,
        label="Evening Peak Period"
    )

    plt.title(
        "Maximum Line Loading in the Network"
    )

    plt.xlabel(
        "Time (Hour)"
    )

    plt.ylabel(
        "Line Loading (%)"
    )

    plt.xlim(0, 24)

    plt.grid(True)

    plt.legend()

    # ========================================================
    # SAVE FIGURE
    # ========================================================

    plt.tight_layout()

    plot_path = os.path.join(
        output_dir,
        "evening_peak_results.png"
    )

    plt.savefig(
        plot_path,
        dpi=300
    )

    plt.show()

    print(f"\nPlot saved to: {plot_path}")


# ============================================================
# 7. MAIN FUNCTION
# ============================================================

def main():

    print("=" * 60)
    print("EV + HEAT PUMP EVENING PEAK SCENARIO")
    print("=" * 60)

    # --------------------------------------------------------
    # Create Network
    # --------------------------------------------------------

    print("\n1. Creating CIGRE LV Network...")

    net = nw.create_cigre_network_lv()

    # --------------------------------------------------------
    # Add EVs
    # --------------------------------------------------------

    print("\n2. Adding EV Chargers...")

    add_evs(net)

    # --------------------------------------------------------
    # Add Heat Pumps
    # --------------------------------------------------------

    print("\n3. Adding Heat Pumps...")

    add_heat_pumps(net)

    # --------------------------------------------------------
    # Power Flow Test
    # --------------------------------------------------------

    print("\n4. Checking initial power flow...")

    pp.runpp(
        net,
        algorithm="bfsw",
        max_iteration=100,
        tolerance_mva=1e-6,
        numba=False
    )

    print("Initial power flow converged.")

    # --------------------------------------------------------
    # Create Profiles
    # --------------------------------------------------------

    print("\n5. Creating load profiles...")

    profiles = create_profiles()

    # --------------------------------------------------------
    # Setup Controllers
    # --------------------------------------------------------

    print("\n6. Setting up time-series controllers...")

    setup_controllers(
        net,
        profiles
    )

    # --------------------------------------------------------
    # Output Writer
    # --------------------------------------------------------

    print("\n7. Configuring OutputWriter...")

    output_dir = create_output_writer(net)

    # --------------------------------------------------------
    # Run Simulation
    # --------------------------------------------------------

    print("\n8. Running 24-hour time-series simulation...")

    run_timeseries(
        net,
        time_steps=range(96),
        run_kwargs={
            "algorithm": "bfsw",
            "max_iteration": 100,
            "tolerance_mva": 1e-6,
            "numba": False
        }
    )

    print("Simulation completed successfully.")

    # --------------------------------------------------------
    # Read Results
    # --------------------------------------------------------

    print("\n9. Reading simulation results...")

    vm_pu_file = os.path.join(
        output_dir,
        "res_bus",
        "vm_pu.json"
    )

    loading_file = os.path.join(
        output_dir,
        "res_line",
        "loading_percent.json"
    )

    vm_pu = pd.read_json(vm_pu_file)

    loading = pd.read_json(loading_file)

    # --------------------------------------------------------
    # Plot Results
    # --------------------------------------------------------

    print("\n10. Generating plots...")

    plot_results(
        profiles,
        vm_pu,
        loading,
        output_dir
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 60)
    print("SIMULATION SUMMARY")
    print("=" * 60)

    print(
        f"Minimum Network Voltage: "
        f"{vm_pu.min().min():.4f} pu"
    )

    print(
        f"Maximum Line Loading: "
        f"{loading.max().max():.2f}%"
    )

    print(
        "\nEvening Peak Period: 17:00 - 22:00"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()