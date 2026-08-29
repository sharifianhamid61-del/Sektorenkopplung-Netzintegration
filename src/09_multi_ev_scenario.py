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


def create_profiles():
    """
    ایجاد پروفایل‌های 24 ساعته
    """

    steps = 96
    t = np.linspace(0, 24, steps, endpoint=False)

    # Household load profile
    household = (
        0.4
        + 0.25 * np.sin((t - 6) * np.pi / 12)
        + 0.35 * np.exp(-((t - 19) ** 2) / 4)
    )

    household = np.clip(household, 0.2, 1.2)

    # EV charging profile
    ev = np.where(
        (t >= 18) | (t < 6),
        1.0,
        0.0
    )

    return pd.DataFrame({
        "household": household,
        "ev": ev
    })


def add_multiple_evs(net):
    """
    اضافه کردن چند شارژر EV به شبکه
    """

    ev_buses = [5, 8, 10, 12, 15]

    for i, bus in enumerate(ev_buses):

        pp.create_load(
            net,
            bus=bus,
            p_mw=0.011,
            q_mvar=0.0,
            scaling=1.0,
            name=f"EV_{i+1}"
        )

    print(f"{len(ev_buses)} EV chargers added.")


def setup_controllers(net, profiles):

    ds = DFData(profiles)

    # بارهای عادی
    normal_loads = net.load[
        ~net.load["name"].astype(str).str.startswith("EV_")
    ].index

    ConstControl(
        net,
        element="load",
        variable="scaling",
        element_index=normal_loads,
        data_source=ds,
        profile_name="household"
    )

    # EV ها
    ev_loads = net.load[
        net.load["name"].astype(str).str.startswith("EV_")
    ].index

    ConstControl(
        net,
        element="load",
        variable="scaling",
        element_index=ev_loads,
        data_source=ds,
        profile_name="ev"
    )


def create_output_writer(net):

    output_dir = os.path.join(
        os.getcwd(),
        "outputs",
        "multi_ev"
    )

    os.makedirs(output_dir, exist_ok=True)

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

    return output_dir


def main():

    print("1. Creating CIGRE LV network...")

    net = nw.create_cigre_network_lv()

    print("2. Adding multiple EV chargers...")

    add_multiple_evs(net)

    print("3. Creating profiles...")

    profiles = create_profiles()

    print("4. Setting controllers...")

    setup_controllers(
        net,
        profiles
    )

    print("5. Setting OutputWriter...")

    output_dir = create_output_writer(net)

    print("6. Running time series simulation...")

    run_timeseries(
        net,
        time_steps=range(96),
        run_kwargs={
            "algorithm": "bfsw",
            "max_iteration": 100,
            "numba": False
        }
    )

    print("Simulation completed.")

    # خواندن نتایج
    vm_pu = pd.read_json(
        os.path.join(
            output_dir,
            "res_bus",
            "vm_pu.json"
        )
    )

    # حداقل ولتاژ هر تایم‌استپ
    min_voltage = vm_pu.min(axis=1)

    plt.figure(figsize=(10, 5))

    plt.plot(
        min_voltage.index,
        min_voltage,
        linewidth=2
    )

    plt.axhline(
        0.9,
        linestyle="--",
        label="Voltage Limit"
    )

    plt.title(
        "Minimum Network Voltage with Multiple EVs"
    )

    plt.xlabel("Time Step")

    plt.ylabel("Voltage (p.u.)")

    plt.grid(True)

    plt.legend()

    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    main()