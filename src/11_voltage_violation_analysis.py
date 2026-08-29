import os
import pandas as pd
import matplotlib.pyplot as plt


def analyze_voltage():

    results_dir = os.path.join(
        os.getcwd(),
        "outputs",
        "evening_peak",
        "res_bus"
    )

    file_path = os.path.join(
        results_dir,
        "vm_pu.json"
    )

    vm_pu = pd.read_json(file_path)

    voltage_limit = 0.90

    # حداقل ولتاژ هر باس
    min_voltage_per_bus = vm_pu.min()

    # بدترین باس
    worst_bus = min_voltage_per_bus.idxmin()

    worst_voltage = min_voltage_per_bus.min()

    # تعداد نقض ولتاژ
    violations = vm_pu < voltage_limit

    violation_count = violations.sum().sum()

    # زمان‌هایی که حداقل یک نقض داریم
    violation_steps = violations.any(axis=1)

    print("\n========== VOLTAGE ANALYSIS ==========")

    print(
        f"Worst Bus: {worst_bus}"
    )

    print(
        f"Minimum Voltage: {worst_voltage:.4f} pu"
    )

    print(
        f"Total Voltage Violations: {violation_count}"
    )

    print(
        f"Time Steps with Violation: "
        f"{violation_steps.sum()}"
    )

    # رسم حداقل ولتاژ شبکه
    min_voltage = vm_pu.min(axis=1)

    plt.figure(figsize=(12, 5))

    plt.plot(
        min_voltage.index,
        min_voltage,
        linewidth=2,
        label="Minimum Network Voltage"
    )

    plt.axhline(
        voltage_limit,
        linestyle="--",
        label="Voltage Limit (0.90 pu)"
    )

    # مشخص کردن نقاط نقض
    violation_indices = min_voltage[
        min_voltage < voltage_limit
    ]

    plt.scatter(
        violation_indices.index,
        violation_indices
    )

    plt.title(
        "Voltage Violation Analysis"
    )

    plt.xlabel(
        "Time Step"
    )

    plt.ylabel(
        "Voltage (p.u.)"
    )

    plt.grid(True)

    plt.legend()

    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    analyze_voltage()