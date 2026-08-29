import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.getcwd()

BEFORE_DIR = os.path.join(
    BASE_DIR,
    "outputs",
    "evening_peak"
)

AFTER_DIR = os.path.join(
    BASE_DIR,
    "outputs",
    "after_control"
)

OUTPUT_DIR = os.path.join(
    BASE_DIR,
    "outputs",
    "enwg_comparison"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# LOAD RESULTS
# ============================================================

def load_results(results_dir):
    """
    خواندن نتایج Voltage و Line Loading
    """

    voltage_file = os.path.join(
        results_dir,
        "res_bus",
        "vm_pu.json"
    )

    loading_file = os.path.join(
        results_dir,
        "res_line",
        "loading_percent.json"
    )

    if not os.path.exists(voltage_file):
        raise FileNotFoundError(
            f"Voltage result not found:\n{voltage_file}"
        )

    if not os.path.exists(loading_file):
        raise FileNotFoundError(
            f"Line loading result not found:\n{loading_file}"
        )

    voltage = pd.read_json(
        voltage_file
    )

    loading = pd.read_json(
        loading_file
    )

    return voltage, loading


# ============================================================
# CALCULATE KPIs
# ============================================================

def calculate_kpis(voltage, loading):
    """
    محاسبه KPI های اصلی شبکه
    """

    voltage_limit = 0.90
    loading_limit = 100.0

    # --------------------------------------------------------
    # Voltage KPIs
    # --------------------------------------------------------

    minimum_voltage = voltage.min().min()

    worst_voltage_bus = voltage.min().idxmin()

    voltage_violations = (
        voltage < voltage_limit
    )

    voltage_violation_events = (
        voltage_violations.sum().sum()
    )

    voltage_violation_steps = (
        voltage_violations.any(axis=1).sum()
    )

    # --------------------------------------------------------
    # Line Loading KPIs
    # --------------------------------------------------------

    maximum_loading = loading.max().max()

    worst_line = loading.max().idxmax()

    line_overloads = (
        loading > loading_limit
    )

    line_overload_events = (
        line_overloads.sum().sum()
    )

    line_overload_steps = (
        line_overloads.any(axis=1).sum()
    )

    # --------------------------------------------------------
    # Return KPI dictionary
    # --------------------------------------------------------

    return {
        "Minimum Voltage (p.u.)": minimum_voltage,
        "Worst Voltage Bus": str(worst_voltage_bus),
        "Voltage Violation Events": int(
            voltage_violation_events
        ),
        "Voltage Violation Time Steps": int(
            voltage_violation_steps
        ),
        "Maximum Line Loading (%)": maximum_loading,
        "Worst Line": str(worst_line),
        "Line Overload Events": int(
            line_overload_events
        ),
        "Line Overload Time Steps": int(
            line_overload_steps
        )
    }


# ============================================================
# CREATE KPI TABLE
# ============================================================

def create_comparison_table(
    before_kpis,
    after_kpis
):
    """
    ایجاد جدول مقایسه Before / After
    """

    rows = []

    metrics = [
        "Minimum Voltage (p.u.)",
        "Voltage Violation Events",
        "Voltage Violation Time Steps",
        "Maximum Line Loading (%)",
        "Line Overload Events",
        "Line Overload Time Steps"
    ]

    for metric in metrics:

        before_value = before_kpis[metric]
        after_value = after_kpis[metric]

        change = after_value - before_value

        # درصد تغییر
        if before_value != 0:
            change_percent = (
                change / before_value
            ) * 100
        else:
            change_percent = np.nan

        rows.append({
            "KPI": metric,
            "Before §14a": before_value,
            "After §14a": after_value,
            "Change": change,
            "Change (%)": change_percent
        })

    return pd.DataFrame(rows)


# ============================================================
# PRINT RESULTS
# ============================================================

def print_results(
    before_kpis,
    after_kpis
):

    print("\n")
    print("=" * 70)
    print("BEFORE vs AFTER §14a EnWG")
    print("=" * 70)

    print("\n--- BEFORE CONTROL ---")

    print(
        f"Minimum Voltage: "
        f"{before_kpis['Minimum Voltage (p.u.)']:.4f} pu"
    )

    print(
        f"Worst Voltage Bus: "
        f"{before_kpis['Worst Voltage Bus']}"
    )

    print(
        f"Voltage Violation Events: "
        f"{before_kpis['Voltage Violation Events']}"
    )

    print(
        f"Maximum Line Loading: "
        f"{before_kpis['Maximum Line Loading (%)']:.2f}%"
    )

    print(
        f"Worst Line: "
        f"{before_kpis['Worst Line']}"
    )

    print(
        f"Line Overload Events: "
        f"{before_kpis['Line Overload Events']}"
    )

    print("\n--- AFTER CONTROL ---")

    print(
        f"Minimum Voltage: "
        f"{after_kpis['Minimum Voltage (p.u.)']:.4f} pu"
    )

    print(
        f"Worst Voltage Bus: "
        f"{after_kpis['Worst Voltage Bus']}"
    )

    print(
        f"Voltage Violation Events: "
        f"{after_kpis['Voltage Violation Events']}"
    )

    print(
        f"Maximum Line Loading: "
        f"{after_kpis['Maximum Line Loading (%)']:.2f}%"
    )

    print(
        f"Worst Line: "
        f"{after_kpis['Worst Line']}"
    )

    print(
        f"Line Overload Events: "
        f"{after_kpis['Line Overload Events']}"
    )

    print("=" * 70)


# ============================================================
# PLOT VOLTAGE COMPARISON
# ============================================================

def plot_voltage_comparison(
    before_voltage,
    after_voltage
):

    time_hours = np.arange(
        len(before_voltage)
    ) * 0.25

    before_min = before_voltage.min(
        axis=1
    )

    after_min = after_voltage.min(
        axis=1
    )

    plt.figure(
        figsize=(12, 6)
    )

    plt.plot(
        time_hours,
        before_min,
        linewidth=2,
        label="Before §14a"
    )

    plt.plot(
        time_hours,
        after_min,
        linewidth=2,
        label="After §14a"
    )

    plt.axhline(
        0.90,
        linestyle="--",
        label="Voltage Limit (0.90 pu)"
    )

    plt.axvspan(
        17,
        22,
        alpha=0.15,
        label="Evening Peak"
    )

    plt.title(
        "Minimum Network Voltage: Before vs After §14a EnWG"
    )

    plt.xlabel(
        "Time (Hour)"
    )

    plt.ylabel(
        "Minimum Voltage (p.u.)"
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
        "voltage_before_after.png"
    )

    plt.savefig(
        path,
        dpi=300
    )

    plt.show()

    print(
        f"Voltage comparison saved to:\n{path}"
    )


# ============================================================
# PLOT LINE LOADING COMPARISON
# ============================================================

def plot_loading_comparison(
    before_loading,
    after_loading
):

    time_hours = np.arange(
        len(before_loading)
    ) * 0.25

    before_max = before_loading.max(
        axis=1
    )

    after_max = after_loading.max(
        axis=1
    )

    plt.figure(
        figsize=(12, 6)
    )

    plt.plot(
        time_hours,
        before_max,
        linewidth=2,
        label="Before §14a"
    )

    plt.plot(
        time_hours,
        after_max,
        linewidth=2,
        label="After §14a"
    )

    plt.axhline(
        100,
        linestyle="--",
        label="Line Loading Limit (100%)"
    )

    plt.axvspan(
        17,
        22,
        alpha=0.15,
        label="Evening Peak"
    )

    plt.title(
        "Maximum Line Loading: Before vs After §14a EnWG"
    )

    plt.xlabel(
        "Time (Hour)"
    )

    plt.ylabel(
        "Maximum Line Loading (%)"
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
        "line_loading_before_after.png"
    )

    plt.savefig(
        path,
        dpi=300
    )

    plt.show()

    print(
        f"Line loading comparison saved to:\n{path}"
    )


# ============================================================
# PLOT KPI COMPARISON
# ============================================================

def plot_kpi_comparison(comparison):

    plot_data = comparison[
        comparison["KPI"].isin([
            "Voltage Violation Events",
            "Line Overload Events"
        ])
    ].copy()

    x = np.arange(
        len(plot_data)
    )

    width = 0.35

    plt.figure(
        figsize=(10, 6)
    )

    plt.bar(
        x - width / 2,
        plot_data["Before §14a"],
        width,
        label="Before §14a"
    )

    plt.bar(
        x + width / 2,
        plot_data["After §14a"],
        width,
        label="After §14a"
    )

    plt.xticks(
        x,
        [
            "Voltage Violations",
            "Line Overloads"
        ]
    )

    plt.ylabel(
        "Number of Events"
    )

    plt.title(
        "Network Violations: Before vs After §14a EnWG"
    )

    plt.grid(
        axis="y"
    )

    plt.legend()

    plt.tight_layout()

    path = os.path.join(
        OUTPUT_DIR,
        "violation_comparison.png"
    )

    plt.savefig(
        path,
        dpi=300
    )

    plt.show()

    print(
        f"Violation comparison saved to:\n{path}"
    )


# ============================================================
# SAVE COMPARISON TABLE
# ============================================================

def save_results(
    comparison,
    before_kpis,
    after_kpis
):

    csv_path = os.path.join(
        OUTPUT_DIR,
        "enwg_kpi_comparison.csv"
    )

    comparison.to_csv(
        csv_path,
        index=False
    )

    # خلاصه متنی
    summary_path = os.path.join(
        OUTPUT_DIR,
        "enwg_summary.txt"
    )

    with open(
        summary_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "BEFORE vs AFTER §14a EnWG\n"
        )

        file.write(
            "=" * 60 + "\n\n"
        )

        file.write(
            "BEFORE CONTROL\n"
        )

        for key, value in before_kpis.items():

            file.write(
                f"{key}: {value}\n"
            )

        file.write(
            "\nAFTER CONTROL\n"
        )

        for key, value in after_kpis.items():

            file.write(
                f"{key}: {value}\n"
            )

        file.write(
            "\n"
        )

        file.write(
            "KPI COMPARISON\n"
        )

        file.write(
            comparison.to_string(
                index=False
            )
        )

    print(
        f"\nKPI table saved to:\n{csv_path}"
    )

    print(
        f"Summary saved to:\n{summary_path}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("§14a EnWG - BEFORE vs AFTER COMPARISON")
    print("=" * 70)

    # --------------------------------------------------------
    # Load BEFORE
    # --------------------------------------------------------

    print(
        "\n1. Loading BEFORE control results..."
    )

    before_voltage, before_loading = load_results(
        BEFORE_DIR
    )

    # --------------------------------------------------------
    # Load AFTER
    # --------------------------------------------------------

    print(
        "\n2. Loading AFTER control results..."
    )

    after_voltage, after_loading = load_results(
        AFTER_DIR
    )

    # --------------------------------------------------------
    # Calculate KPIs
    # --------------------------------------------------------

    print(
        "\n3. Calculating network KPIs..."
    )

    before_kpis = calculate_kpis(
        before_voltage,
        before_loading
    )

    after_kpis = calculate_kpis(
        after_voltage,
        after_loading
    )

    # --------------------------------------------------------
    # Print results
    # --------------------------------------------------------

    print_results(
        before_kpis,
        after_kpis
    )

    # --------------------------------------------------------
    # Create table
    # --------------------------------------------------------

    comparison = create_comparison_table(
        before_kpis,
        after_kpis
    )

    print("\nKPI COMPARISON TABLE\n")

    print(
        comparison.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # Plot voltage
    # --------------------------------------------------------

    print(
        "\n4. Generating voltage comparison..."
    )

    plot_voltage_comparison(
        before_voltage,
        after_voltage
    )

    # --------------------------------------------------------
    # Plot line loading
    # --------------------------------------------------------

    print(
        "\n5. Generating line loading comparison..."
    )

    plot_loading_comparison(
        before_loading,
        after_loading
    )

    # --------------------------------------------------------
    # Plot violations
    # --------------------------------------------------------

    print(
        "\n6. Generating violation comparison..."
    )

    plot_kpi_comparison(
        comparison
    )

    # --------------------------------------------------------
    # Save results
    # --------------------------------------------------------

    print(
        "\n7. Saving KPI results..."
    )

    save_results(
        comparison,
        before_kpis,
        after_kpis
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "§14a EnWG comparison completed successfully."
    )

    print(
        f"All results saved in:\n{OUTPUT_DIR}"
    )

    print(
        "=" * 70
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()