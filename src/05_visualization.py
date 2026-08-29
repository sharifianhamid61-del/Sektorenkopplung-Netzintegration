import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os


# ============================================================
# 0. PROJECT PATHS
# ============================================================

# مسیر ریشه پروژه، مستقل از محل اجرای اسکریپت
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# مسیر پوشه outputs
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# مسیر فایل‌های ورودی
PATH_VOLTAGE = os.path.join(OUTPUT_DIR, "ts_vm_pu.csv")
PATH_LOADING = os.path.join(OUTPUT_DIR, "ts_line_loading.csv")


# ============================================================
# 1. CHECK INPUT FILES
# ============================================================

print("==========================================")
print("Loading data...")
print("Project directory:", BASE_DIR)
print("Output directory:", OUTPUT_DIR)
print("Voltage file:", PATH_VOLTAGE)
print("Loading file:", PATH_LOADING)
print("==========================================")


# بررسی وجود فایل ولتاژ
if not os.path.exists(PATH_VOLTAGE):
    raise FileNotFoundError(
        f"\nVoltage file not found:\n{PATH_VOLTAGE}"
    )


# بررسی وجود فایل بارگیری خطوط
if not os.path.exists(PATH_LOADING):
    raise FileNotFoundError(
        f"\nLoading file not found:\n{PATH_LOADING}"
    )


print("Input files found successfully.")


# ============================================================
# 2. READ DATA
# ============================================================

df_vm = pd.read_csv(PATH_VOLTAGE, index_col=0)
df_loading = pd.read_csv(PATH_LOADING, index_col=0)

print("Voltage data shape:", df_vm.shape)
print("Loading data shape:", df_loading.shape)


# ============================================================
# 3. BASIC DATA VALIDATION
# ============================================================

if df_vm.empty:
    raise ValueError("Voltage dataframe is empty.")

if df_loading.empty:
    raise ValueError("Loading dataframe is empty.")


print("Data loaded successfully.")


# ============================================================
# 4. NETWORK INDICES
# ============================================================

# حداقل ولتاژ در هر ساعت برای کل شبکه
min_voltage_series = df_vm.min(axis=1)

# حداکثر بارگیری خطوط در هر ساعت برای کل شبکه
max_loading_series = df_loading.max(axis=1)


# ============================================================
# 5. SUMMARY
# ============================================================

absolute_min_voltage = min_voltage_series.min()
absolute_max_loading = max_loading_series.max()

min_voltage_hour = min_voltage_series.idxmin()
max_loading_hour = max_loading_series.idxmax()


print("\n==========================================")
print("NETWORK SUMMARY")
print("==========================================")

print(
    f"Absolute Minimum Voltage : "
    f"{absolute_min_voltage:.4f} p.u."
)

print(
    f"Hour of Minimum Voltage  : "
    f"{min_voltage_hour}"
)

print(
    f"Absolute Maximum Loading : "
    f"{absolute_max_loading:.2f} %"
)

print(
    f"Hour of Maximum Loading  : "
    f"{max_loading_hour}"
)

print("==========================================")


# ============================================================
# 6. PLOT 1 - MINIMUM VOLTAGE
# ============================================================

plt.figure(figsize=(14, 5))

plt.plot(
    min_voltage_series.values,
    color="#1f77b4",
    linewidth=0.5,
    alpha=0.9,
    label="Minimum Voltage"
)

# حد پایین ولتاژ
plt.axhline(
    y=0.9,
    color="red",
    linestyle="--",
    linewidth=1.5,
    label="Lower Limit (0.9 p.u.)"
)

plt.title(
    "Minimum Grid Voltage over 1 Year (Base Case H0)",
    fontsize=14,
    fontweight="bold"
)

plt.xlabel(
    "Hour of the Year (8760 h)",
    fontsize=12
)

plt.ylabel(
    "Voltage [p.u.]",
    fontsize=12
)

plt.ylim(0.85, 1.05)

plt.legend(loc="lower right")

plt.grid(
    True,
    linestyle=":",
    alpha=0.7
)

plt.tight_layout()


# ============================================================
# 7. SAVE VOLTAGE PLOT
# ============================================================

VOLTAGE_PLOT = os.path.join(
    OUTPUT_DIR,
    "base_case_voltage.png"
)

plt.savefig(
    VOLTAGE_PLOT,
    dpi=300,
    bbox_inches="tight"
)

print(
    f"\nVoltage plot saved to:\n{VOLTAGE_PLOT}"
)

plt.show()


# ============================================================
# 8. PLOT 2 - MAXIMUM LINE LOADING
# ============================================================

plt.figure(figsize=(14, 5))

plt.plot(
    max_loading_series.values,
    color="#ff7f0e",
    linewidth=0.5,
    alpha=0.9,
    label="Maximum Line Loading"
)

# حد اضافه بار
plt.axhline(
    y=100,
    color="red",
    linestyle="--",
    linewidth=1.5,
    label="Overload Limit (100%)"
)

plt.title(
    "Maximum Line Loading over 1 Year (Base Case H0)",
    fontsize=14,
    fontweight="bold"
)

plt.xlabel(
    "Hour of the Year (8760 h)",
    fontsize=12
)

plt.ylabel(
    "Line Loading [%]",
    fontsize=12
)

plt.ylim(0, 110)

plt.legend(loc="upper right")

plt.grid(
    True,
    linestyle=":",
    alpha=0.7
)

plt.tight_layout()


# ============================================================
# 9. SAVE LOADING PLOT
# ============================================================

LOADING_PLOT = os.path.join(
    OUTPUT_DIR,
    "base_case_loading.png"
)

plt.savefig(
    LOADING_PLOT,
    dpi=300,
    bbox_inches="tight"
)

print(
    f"Loading plot saved to:\n{LOADING_PLOT}"
)

plt.show()


# ============================================================
# 10. FINAL MESSAGE
# ============================================================

print("\n==========================================")
print("VISUALIZATION COMPLETED SUCCESSFULLY")
print("==========================================")

print(
    f"Minimum Voltage : {absolute_min_voltage:.4f} p.u."
)

print(
    f"Maximum Loading : {absolute_max_loading:.2f} %"
)

print(
    f"Voltage plot    : {VOLTAGE_PLOT}"
)

print(
    f"Loading plot    : {LOADING_PLOT}"
)

print("==========================================")