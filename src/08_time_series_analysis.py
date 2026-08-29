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


def create_synthetic_profiles():
    """
    ایجاد پروفایل‌های 24 ساعته با رزولوشن 15 دقیقه‌ای
    """

    steps = 96
    t = np.linspace(0, 24, steps, endpoint=False)

    # پروفایل مصرف خانگی
    household = (
        0.35
        + 0.25 * np.sin((t - 6) * np.pi / 12)
        + 0.45 * np.exp(-((t - 19) ** 2) / 5)
    )

    # جلوگیری از مقادیر خیلی پایین
    household = np.clip(household, 0.2, None)

    # پروفایل تولید خورشیدی
    pv = np.clip(
        np.sin((t - 6) * np.pi / 12),
        0,
        1
    )

    # پروفایل شارژ EV
    ev = np.where(
        (t >= 18) | (t < 6),
        1.0,
        0.0
    )

    profiles = pd.DataFrame({
        "household": household,
        "pv": pv,
        "ev": ev
    })

    return profiles


def setup_timeseries_simulation(net, profiles):
    """
    اتصال پروفایل‌های زمانی به شبکه
    """

    ds = DFData(profiles)

    # بارهای معمولی شبکه
    normal_loads = net.load[
        net.load["name"] != "EV_Charger"
    ].index

    if len(normal_loads) > 0:
        ConstControl(
            net,
            element="load",
            variable="scaling",
            element_index=normal_loads,
            data_source=ds,
            profile_name="household"
        )

    # بار EV
    ev_loads = net.load[
        net.load["name"] == "EV_Charger"
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

    # سیستم PV
    pv_generators = net.sgen[
        net.sgen["name"] == "PV_System"
    ].index

    if len(pv_generators) > 0:
        ConstControl(
            net,
            element="sgen",
            variable="scaling",
            element_index=pv_generators,
            data_source=ds,
            profile_name="pv"
        )


def create_output_writer(net):
    """
    تنظیمات ذخیره نتایج
    """

    output_dir = os.path.join(
        os.getcwd(),
        "outputs",
        "timeseries"
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

    ow.log_variable(
        "res_bus",
        "vm_pu"
    )

    ow.log_variable(
        "res_line",
        "loading_percent"
    )

    return ow, output_dir


def run_and_plot():

    print("1. Creating CIGRE LV Grid...")

    net = nw.create_cigre_network_lv()

    # تست اولیه شبکه
    print("Checking initial power flow...")

    pp.runpp(
        net,
        algorithm="bfsw",
        max_iteration=100,
        tolerance_mva=1e-6,
        numba=False
    )

    print("Initial power flow converged.")

    # اضافه کردن PV و EV
    print("2. Adding PV System and EV Charger...")

    pp.create_sgen(
        net,
        bus=10,
        p_mw=0.03,
        q_mvar=0.0,
        name="PV_System",
        scaling=1.0
    )

    pp.create_load(
        net,
        bus=12,
        p_mw=0.011,
        q_mvar=0.0,
        name="EV_Charger",
        scaling=1.0
    )

    # تست شبکه بعد از اضافه شدن تجهیزات
    print("Checking network after adding PV and EV...")

    pp.runpp(
        net,
        algorithm="bfsw",
        max_iteration=100,
        tolerance_mva=1e-6,
        numba=False
    )

    print("Network configuration is stable.")

    # ساخت پروفایل‌ها
    print("3. Generating Load/Generation Profiles...")

    profiles = create_synthetic_profiles()

    # کنترلرها
    print("4. Setting up Controllers...")

    setup_timeseries_simulation(
        net,
        profiles
    )

    # Output Writer
    print("5. Configuring Output Writer...")

    ow, output_dir = create_output_writer(net)

    # اجرای Time Series
    print(
        "6. Running Time Series Simulation for 24h (96 steps)..."
    )

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

    # خواندن نتایج
    print("7. Processing and Plotting Results...")

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

    # محور زمان
    time_hours = np.arange(96) * 0.25

    # رسم نمودار
    plt.figure(figsize=(12, 10))

    # نمودار ولتاژ
    plt.subplot(2, 1, 1)

    plt.plot(
        time_hours,
        vm_pu[12],
        label="Bus 12 (EV Node)",
        linewidth=2
    )

    plt.plot(
        time_hours,
        vm_pu[10],
        label="Bus 10 (PV Node)",
        linewidth=2
    )

    plt.axhline(
        0.9,
        linestyle="--",
        label="Lower Limit (0.9 pu)"
    )

    plt.axhline(
        1.1,
        linestyle="--",
        label="Upper Limit (1.1 pu)"
    )

    plt.title("24-Hour Voltage Profile")
    plt.xlabel("Time (Hour)")
    plt.ylabel("Voltage (p.u.)")

    plt.xlim(0, 24)
    plt.grid(True)
    plt.legend()

    # نمودار بارگذاری خطوط
    plt.subplot(2, 1, 2)

    max_loading = loading.max(axis=1)

    plt.plot(
        time_hours,
        max_loading,
        label="Maximum Network Line Loading",
        linewidth=2
    )

    plt.axhline(
        100,
        linestyle="--",
        label="100% Limit"
    )

    plt.title("Maximum Line Loading Over 24 Hours")
    plt.xlabel("Time (Hour)")
    plt.ylabel("Loading (%)")

    plt.xlim(0, 24)
    plt.grid(True)
    plt.legend()

    plt.tight_layout()

    # ذخیره نمودار
    plot_path = os.path.join(
        os.getcwd(),
        "outputs",
        "timeseries_results.png"
    )

    plt.savefig(
        plot_path,
        dpi=300
    )

    plt.show()

    print("\nSimulation successful!")
    print(f"Plot saved to: {plot_path}")


if __name__ == "__main__":
    run_and_plot()