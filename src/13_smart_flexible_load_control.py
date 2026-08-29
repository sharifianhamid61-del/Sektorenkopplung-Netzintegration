
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import pandapower as pp
import pandapower.networks as nw


# ============================================================
# CONFIGURATION
# ============================================================

STEPS = 96

# حدود فنی شبکه
VOLTAGE_LIMIT = 0.90
VOLTAGE_CONTROL_THRESHOLD = 0.93

LINE_LIMIT = 100.0
LINE_CONTROL_THRESHOLD = 90.0

# میزان کاهش بار در هر اقدام کنترلی
EV_REDUCTION_STEP = 0.20
HP_REDUCTION_STEP = 0.15

# حداقل توان قابل استفاده از بار انعطاف پذیر
MIN_EV_SCALING = 0.20
MIN_HP_SCALING = 0.30

# حداکثر تعداد تلاش کنترل در هر Time Step
MAX_CONTROL_ITERATIONS = 10

# مسیر خروجی
OUTPUT_DIR = os.path.join(
    os.getcwd(),
    "outputs",
    "after_control"
)


# ============================================================
# 1. CREATE LOAD PROFILES
# ============================================================

def create_profiles():
    """
    ایجاد پروفایل‌های 24 ساعته با رزولوشن 15 دقیقه‌ای.
    """

    # 96 استپ، هر استپ 15 دقیقه
    time_hours = np.arange(STEPS) * 0.25

    # --------------------------------------------------------
    # Household Load Profile
    # --------------------------------------------------------

    household = (
        0.35
        + 0.20 * np.sin(
            (time_hours - 6) * np.pi / 12
        )
        + 0.55 * np.exp(
            -((time_hours - 19) ** 2) / 4
        )
    )

    household = np.clip(
        household,
        0.20,
        1.30
    )

    # --------------------------------------------------------
    # EV Charging Profile
    # فعال از 18:00 تا 06:00
    # --------------------------------------------------------

    ev = np.where(
        (time_hours >= 18) | (time_hours < 6),
        1.0,
        0.0
    )

    # --------------------------------------------------------
    # Heat Pump Profile
    # پیک در ساعات عصر
    # --------------------------------------------------------

    hp = np.where(
        (time_hours >= 17) & (time_hours <= 22),
        1.0,
        0.40
    )

    # --------------------------------------------------------
    # Evening Peak Indicator
    # --------------------------------------------------------

    evening_peak = np.where(
        (time_hours >= 17) & (time_hours <= 22),
        1.0,
        0.0
    )

    profiles = pd.DataFrame({
        "time_hour": time_hours,
        "household": household,
        "ev": ev,
        "hp": hp,
        "evening_peak": evening_peak
    })

    return profiles


# ============================================================
# 2. ADD EV CHARGERS
# ============================================================

def add_evs(net):
    """
    اضافه کردن چند شارژر EV به باس‌های مختلف شبکه.
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

    print(
        f"{len(ev_buses)} EV chargers added."
    )


# ============================================================
# 3. ADD HEAT PUMPS
# ============================================================

def add_heat_pumps(net):
    """
    اضافه کردن Heat Pump به باس‌های مختلف.
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

    print(
        f"{len(hp_buses)} Heat Pumps added."
    )


# ============================================================
# 4. IDENTIFY LOAD GROUPS
# ============================================================

def get_load_groups(net):
    """
    شناسایی سه گروه بار:
    Household
    EV
    Heat Pump
    """

    names = net.load["name"].astype(str)

    household_indices = net.load[
        ~names.str.startswith(("EV_", "HP_"))
    ].index.tolist()

    ev_indices = net.load[
        names.str.startswith("EV_")
    ].index.tolist()

    hp_indices = net.load[
        names.str.startswith("HP_")
    ].index.tolist()

    return (
        household_indices,
        ev_indices,
        hp_indices
    )


# ============================================================
# 5. APPLY SCALINGS
# ============================================================

def apply_scalings(
    net,
    household_indices,
    ev_indices,
    hp_indices,
    household_scaling,
    ev_scaling,
    hp_scaling
):
    """
    اعمال Scaling به Household، EV و Heat Pump.
    """

    if len(household_indices) > 0:

        net.load.loc[
            household_indices,
            "scaling"
        ] = household_scaling

    if len(ev_indices) > 0:

        net.load.loc[
            ev_indices,
            "scaling"
        ] = ev_scaling

    if len(hp_indices) > 0:

        net.load.loc[
            hp_indices,
            "scaling"
        ] = hp_scaling


# ============================================================
# 6. RUN POWER FLOW
# ============================================================

def run_power_flow(net):
    """
    اجرای Power Flow با BFSW.
    """

    pp.runpp(
        net,
        algorithm="bfsw",
        max_iteration=100,
        tolerance_mva=1e-6,
        numba=False
    )


# ============================================================
# 7. GET NETWORK STATUS
# ============================================================

def get_network_status(net):
    """
    استخراج:
    Minimum Voltage
    Maximum Line Loading
    """

    min_voltage = net.res_bus[
        "vm_pu"
    ].min()

    max_loading = net.res_line[
        "loading_percent"
    ].max()

    # اگر شبکه خط نداشت
    if pd.isna(max_loading):
        max_loading = 0.0

    return (
        float(min_voltage),
        float(max_loading)
    )


# ============================================================
# 8. SMART FLEXIBLE LOAD CONTROL
# ============================================================

def smart_control_step(
    net,
    household_indices,
    ev_indices,
    hp_indices,
    household_scaling,
    requested_ev_scaling,
    requested_hp_scaling
):
    """
    کنترل هوشمند EV و Heat Pump برای یک Time Step.

    منطق:

    1. EV و HP در حالت درخواست‌شده قرار می‌گیرند.
    2. Power Flow اجرا می‌شود.
    3. اگر:
       V < 0.93 pu
       یا
       Loading > 90%
       باشد، کنترل فعال می‌شود.
    4. ابتدا EV کاهش داده می‌شود.
    5. اگر وضعیت همچنان نامناسب باشد، HP نیز کاهش داده می‌شود.
    6. بعد از هر تغییر Power Flow مجدداً اجرا می‌شود.
    """

    ev_scaling = float(
        requested_ev_scaling
    )

    hp_scaling = float(
        requested_hp_scaling
    )

    control_iterations = 0

    # --------------------------------------------------------
    # Initial state
    # --------------------------------------------------------

    apply_scalings(
        net,
        household_indices,
        ev_indices,
        hp_indices,
        household_scaling,
        ev_scaling,
        hp_scaling
    )

    run_power_flow(net)

    min_voltage, max_loading = get_network_status(
        net
    )

    # --------------------------------------------------------
    # Smart Control Loop
    # --------------------------------------------------------

    while (
        (
            min_voltage < VOLTAGE_CONTROL_THRESHOLD
            or
            max_loading > LINE_CONTROL_THRESHOLD
        )
        and
        control_iterations < MAX_CONTROL_ITERATIONS
    ):

        control_iterations += 1

        previous_ev = ev_scaling
        previous_hp = hp_scaling

        # ----------------------------------------------------
        # First priority: EV
        # ----------------------------------------------------

        if (
            min_voltage < VOLTAGE_CONTROL_THRESHOLD
            or
            max_loading > LINE_CONTROL_THRESHOLD
        ):

            ev_scaling = max(
                MIN_EV_SCALING,
                ev_scaling * (
                    1.0 - EV_REDUCTION_STEP
                )
            )

        # ----------------------------------------------------
        # Second priority: Heat Pump
        #
        # زمانی فعال می‌شود که نقض واقعی حد فنی وجود داشته
        # باشد یا EV دیگر قابل کاهش نباشد.
        # ----------------------------------------------------

        if (
            (
                min_voltage < VOLTAGE_LIMIT
                or
                max_loading > LINE_LIMIT
            )
            or
            ev_scaling <= MIN_EV_SCALING
        ):

            hp_scaling = max(
                MIN_HP_SCALING,
                hp_scaling * (
                    1.0 - HP_REDUCTION_STEP
                )
            )

        # ----------------------------------------------------
        # اگر هیچ تغییری ایجاد نشد، از حلقه خارج شو
        # ----------------------------------------------------

        if (
            ev_scaling == previous_ev
            and
            hp_scaling == previous_hp
        ):
            break

        # ----------------------------------------------------
        # Apply new scaling
        # ----------------------------------------------------

        apply_scalings(
            net,
            household_indices,
            ev_indices,
            hp_indices,
            household_scaling,
            ev_scaling,
            hp_scaling
        )

        # ----------------------------------------------------
        # Re-run power flow
        # ----------------------------------------------------

        run_power_flow(net)

        min_voltage, max_loading = get_network_status(
            net
        )

    return {
        "ev_scaling": ev_scaling,
        "hp_scaling": hp_scaling,
        "min_voltage": min_voltage,
        "max_loading": max_loading,
        "control_iterations": control_iterations
    }


# ============================================================
# 9. SAVE RESULTS
# ============================================================

def save_results(
    voltage_results,
    loading_results,
    control_results
):
    """
    ذخیره نتایج.

    نکته مهم:
    اندیس Time Series به صورت 0 تا 95 ساخته می‌شود
    تا مشکل duplicate index در to_json ایجاد نشود.
    """

    # --------------------------------------------------------
    # Create directories
    # --------------------------------------------------------

    bus_dir = os.path.join(
        OUTPUT_DIR,
        "res_bus"
    )

    line_dir = os.path.join(
        OUTPUT_DIR,
        "res_line"
    )

    os.makedirs(
        bus_dir,
        exist_ok=True
    )

    os.makedirs(
        line_dir,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Voltage DataFrame
    # --------------------------------------------------------

    voltage_df = pd.DataFrame(
        voltage_results
    )

    # اطمینان از یکتا بودن index
    voltage_df = voltage_df.reset_index(
        drop=True
    )

    voltage_df.index = np.arange(
        len(voltage_df)
    )

    voltage_df.index.name = "time_step"

    voltage_path = os.path.join(
        bus_dir,
        "vm_pu.json"
    )

    voltage_df.to_json(
        voltage_path,
        orient="columns"
    )

    # --------------------------------------------------------
    # Line Loading DataFrame
    # --------------------------------------------------------

    loading_df = pd.DataFrame(
        loading_results
    )

    loading_df = loading_df.reset_index(
        drop=True
    )

    loading_df.index = np.arange(
        len(loading_df)
    )

    loading_df.index.name = "time_step"

    loading_path = os.path.join(
        line_dir,
        "loading_percent.json"
    )

    loading_df.to_json(
        loading_path,
        orient="columns"
    )

    # --------------------------------------------------------
    # Control Actions
    # --------------------------------------------------------

    control_df = pd.DataFrame(
        control_results
    )

    control_df = control_df.reset_index(
        drop=True
    )

    control_path = os.path.join(
        OUTPUT_DIR,
        "control_actions.csv"
    )

    control_df.to_csv(
        control_path,
        index=False
    )

    print("\nResults saved successfully:")
    print(
        f"Voltage results: {voltage_path}"
    )
    print(
        f"Line loading results: {loading_path}"
    )
    print(
        f"Control actions: {control_path}"
    )

    return (
        voltage_df,
        loading_df,
        control_df
    )


# ============================================================
# 10. PLOT FLEXIBLE LOAD CONTROL
# ============================================================

def plot_flexible_load_control(control_df):
    """
    نمودار مقایسه EV و Heat Pump قبل و بعد از کنترل.
    """

    time_hours = control_df[
        "time_hour"
    ].values

    plt.figure(
        figsize=(12, 6)
    )

    plt.plot(
        time_hours,
        control_df["ev_requested_scaling"],
        linewidth=2,
        label="EV Requested"
    )

    plt.plot(
        time_hours,
        control_df["ev_scaling"],
        linewidth=2,
        label="EV Controlled"
    )

    plt.plot(
        time_hours,
        control_df["hp_requested_scaling"],
        linewidth=2,
        label="HP Requested"
    )

    plt.plot(
        time_hours,
        control_df["hp_scaling"],
        linewidth=2,
        label="HP Controlled"
    )

    plt.axvspan(
        17,
        22,
        alpha=0.15,
        label="Evening Peak"
    )

    plt.title(
        "Flexible Load Control: EV and Heat Pump"
    )

    plt.xlabel(
        "Time (Hour)"
    )

    plt.ylabel(
        "Scaling Factor"
    )

    plt.xlim(
        0,
        24
    )

    plt.grid(
        True
    )

    plt.legend()

    plt.tight_layout()

    path = os.path.join(
        OUTPUT_DIR,
        "flexible_load_control.png"
    )

    plt.savefig(
        path,
        dpi=300
    )

    plt.show()

    print(
        f"Flexible load plot saved to:\n{path}"
    )


# ============================================================
# 11. PLOT CONTROLLED VOLTAGE
# ============================================================

def plot_controlled_voltage(control_df):
    """
    نمودار Minimum Voltage بعد از کنترل.
    """

    time_hours = control_df[
        "time_hour"
    ].values

    plt.figure(
        figsize=(12, 6)
    )

    plt.plot(
        time_hours,
        control_df["min_voltage"],
        linewidth=2,
        label="Minimum Network Voltage"
    )

    plt.axhline(
        VOLTAGE_LIMIT,
        linestyle="--",
        label="Voltage Limit (0.90 pu)"
    )

    plt.axhline(
        VOLTAGE_CONTROL_THRESHOLD,
        linestyle=":",
        label="Control Threshold (0.93 pu)"
    )

    plt.axvspan(
        17,
        22,
        alpha=0.15,
        label="Evening Peak"
    )

    plt.title(
        "Minimum Voltage After Flexible Load Control"
    )

    plt.xlabel(
        "Time (Hour)"
    )

    plt.ylabel(
        "Voltage (p.u.)"
    )

    plt.xlim(
        0,
        24
    )

    plt.grid(
        True
    )

    plt.legend()

    plt.tight_layout()

    path = os.path.join(
        OUTPUT_DIR,
        "controlled_voltage.png"
    )

    plt.savefig(
        path,
        dpi=300
    )

    plt.show()

    print(
        f"Voltage plot saved to:\n{path}"
    )


# ============================================================
# 12. PLOT CONTROLLED LINE LOADING
# ============================================================

def plot_controlled_line_loading(control_df):
    """
    نمودار Maximum Line Loading بعد از کنترل.
    """

    time_hours = control_df[
        "time_hour"
    ].values

    plt.figure(
        figsize=(12, 6)
    )

    plt.plot(
        time_hours,
        control_df["max_loading"],
        linewidth=2,
        label="Maximum Line Loading"
    )

    plt.axhline(
        LINE_LIMIT,
        linestyle="--",
        label="Line Limit (100%)"
    )

    plt.axhline(
        LINE_CONTROL_THRESHOLD,
        linestyle=":",
        label="Control Threshold (90%)"
    )

    plt.axvspan(
        17,
        22,
        alpha=0.15,
        label="Evening Peak"
    )

    plt.title(
        "Maximum Line Loading After Flexible Load Control"
    )

    plt.xlabel(
        "Time (Hour)"
    )

    plt.ylabel(
        "Line Loading (%)"
    )

    plt.xlim(
        0,
        24
    )

    plt.grid(
        True
    )

    plt.legend()

    plt.tight_layout()

    path = os.path.join(
        OUTPUT_DIR,
        "controlled_line_loading.png"
    )

    plt.savefig(
        path,
        dpi=300
    )

    plt.show()

    print(
        f"Line loading plot saved to:\n{path}"
    )


# ============================================================
# 13. MAIN
# ============================================================

def main():

    print("=" * 70)
    print("SMART FLEXIBLE LOAD CONTROL")
    print("=" * 70)

    # --------------------------------------------------------
    # Create network
    # --------------------------------------------------------

    print(
        "\n1. Creating CIGRE LV Network..."
    )

    net = nw.create_cigre_network_lv()

    # --------------------------------------------------------
    # Add EVs
    # --------------------------------------------------------

    print(
        "\n2. Adding EV chargers..."
    )

    add_evs(
        net
    )

    # --------------------------------------------------------
    # Add Heat Pumps
    # --------------------------------------------------------

    print(
        "\n3. Adding Heat Pumps..."
    )

    add_heat_pumps(
        net
    )

    # --------------------------------------------------------
    # Initial power flow
    # --------------------------------------------------------

    print(
        "\n4. Checking initial network..."
    )

    run_power_flow(
        net
    )

    print(
        "Initial power flow converged."
    )

    # --------------------------------------------------------
    # Identify load groups
    # --------------------------------------------------------

    (
        household_indices,
        ev_indices,
        hp_indices
    ) = get_load_groups(
        net
    )

    print(
        f"Household loads: "
        f"{len(household_indices)}"
    )

    print(
        f"EV loads: "
        f"{len(ev_indices)}"
    )

    print(
        f"Heat Pump loads: "
        f"{len(hp_indices)}"
    )

    # --------------------------------------------------------
    # Create profiles
    # --------------------------------------------------------

    print(
        "\n5. Creating profiles..."
    )

    profiles = create_profiles()

    # --------------------------------------------------------
    # Result containers
    # --------------------------------------------------------

    voltage_results = []

    loading_results = []

    control_results = []

    # --------------------------------------------------------
    # Time-Series Simulation
    # --------------------------------------------------------

    print(
        "\n6. Starting smart control simulation..."
    )

    for step in range(STEPS):

        time_hour = profiles.loc[
            step,
            "time_hour"
        ]

        household_scaling = profiles.loc[
            step,
            "household"
        ]

        requested_ev = profiles.loc[
            step,
            "ev"
        ]

        requested_hp = profiles.loc[
            step,
            "hp"
        ]

        # ----------------------------------------------------
        # Smart control
        # ----------------------------------------------------

        result = smart_control_step(
            net,
            household_indices,
            ev_indices,
            hp_indices,
            household_scaling,
            requested_ev,
            requested_hp
        )

        # ----------------------------------------------------
        # Save bus voltage results
        # ----------------------------------------------------

        voltage_results.append(
            net.res_bus[
                "vm_pu"
            ].to_numpy()
        )

        # ----------------------------------------------------
        # Save line loading results
        # ----------------------------------------------------

        loading_results.append(
            net.res_line[
                "loading_percent"
            ].to_numpy()
        )

        # ----------------------------------------------------
        # Save control results
        # ----------------------------------------------------

        control_results.append({

            "time_step": step,

            "time_hour": time_hour,

            "household_scaling":
                household_scaling,

            "ev_requested_scaling":
                requested_ev,

            "ev_scaling":
                result["ev_scaling"],

            "hp_requested_scaling":
                requested_hp,

            "hp_scaling":
                result["hp_scaling"],

            "min_voltage":
                result["min_voltage"],

            "max_loading":
                result["max_loading"],

            "control_iterations":
                result["control_iterations"]
        })

        # ----------------------------------------------------
        # Progress
        # ----------------------------------------------------

        if (
            step % 8 == 0
            or
            result["control_iterations"] > 0
        ):

            print(
                f"Time {time_hour:05.2f} h | "
                f"Min V = "
                f"{result['min_voltage']:.4f} pu | "
                f"Max Loading = "
                f"{result['max_loading']:.2f}% | "
                f"EV = "
                f"{result['ev_scaling']:.2f} | "
                f"HP = "
                f"{result['hp_scaling']:.2f} | "
                f"Control Iterations = "
                f"{result['control_iterations']}"
            )

    # --------------------------------------------------------
    # Save all results
    # --------------------------------------------------------

    print(
        "\n7. Saving results..."
    )

    (
        voltage_df,
        loading_df,
        control_df
    ) = save_results(
        voltage_results,
        loading_results,
        control_results
    )

    # --------------------------------------------------------
    # Generate plots
    # --------------------------------------------------------

    print(
        "\n8. Generating plots..."
    )

    plot_flexible_load_control(
        control_df
    )

    plot_controlled_voltage(
        control_df
    )

    plot_controlled_line_loading(
        control_df
    )

    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    voltage_violations = (
        control_df["min_voltage"]
        < VOLTAGE_LIMIT
    )

    line_overloads = (
        control_df["max_loading"]
        > LINE_LIMIT
    )

    control_actions = (
        control_df["control_iterations"]
        > 0
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "SMART CONTROL SUMMARY"
    )

    print(
        "=" * 70
    )

    print(
        f"Minimum Network Voltage: "
        f"{voltage_df.min().min():.4f} pu"
    )

    print(
        f"Maximum Line Loading: "
        f"{loading_df.max().max():.2f}%"
    )

    print(
        f"Minimum EV Scaling: "
        f"{control_df['ev_scaling'].min():.2f}"
    )

    print(
        f"Minimum HP Scaling: "
        f"{control_df['hp_scaling'].min():.2f}"
    )

    print(
        f"Time Steps with Control Action: "
        f"{control_actions.sum()}"
    )

    print(
        f"Voltage Violation Time Steps: "
        f"{voltage_violations.sum()}"
    )

    print(
        f"Line Overload Time Steps: "
        f"{line_overloads.sum()}"
    )

    print(
        "\nResults saved in:"
    )

    print(
        OUTPUT_DIR
    )

    print(
        "=" * 70
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
