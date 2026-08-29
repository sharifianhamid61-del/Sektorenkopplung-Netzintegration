import os
import pandas as pd
import matplotlib.pyplot as plt


def analyze_line_loading():

    results_dir = os.path.join(
        os.getcwd(),
        "outputs",
        "evening_peak",
        "res_line"
    )

    file_path = os.path.join(
        results_dir,
        "loading_percent.json"
    )

    loading = pd.read_json(file_path)

    loading_limit = 100.0

    # حداکثر بارگذاری هر خط
    max_loading_per_line = loading.max()

    # بدترین خط
    worst_line = max_loading_per_line.idxmax()

    worst_loading = max_loading_per_line.max()

    # تشخیص اضافه بار
    overload = loading > loading_limit

    overload_count = overload.sum().sum()

    overload_steps = overload.any(axis=1)

    print("\n========== LINE LOADING ANALYSIS ==========")

    print(
        f"Worst Line: {worst_line}"
    )

    print(
        f"Maximum Loading: {worst_loading:.2f}%"
    )

    print(
        f"Total Overload Events: {overload_count}"
    )

    print(
        f"Time Steps with Overload: "
        f"{overload_steps.sum()}"
    )

    # حداکثر بارگذاری شبکه در هر زمان
    max_loading = loading.max(axis=1)

    plt.figure(figsize=(12, 5))

    plt.plot(
        max_loading.index,
        max_loading,
        linewidth=2,
        label="Maximum Line Loading"
    )

    plt.axhline(
        loading_limit,
        linestyle="--",
        label="100% Limit"
    )

    overload_indices = max_loading[
        max_loading > loading_limit
    ]

    plt.scatter(
        overload_indices.index,
        overload_indices
    )

    plt.title(
        "Line Overloading Analysis"
    )

    plt.xlabel(
        "Time Step"
    )

    plt.ylabel(
        "Line Loading (%)"
    )

    plt.grid(True)

    plt.legend()

    plt.tight_layout()

    plt.show()


if __name__ == "__main__":
    analyze_line_loading()