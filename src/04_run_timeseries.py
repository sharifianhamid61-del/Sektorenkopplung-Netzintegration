"""
04_run_timeseries.py

Pandapower Time-Series Analysis Script:
1. Loads the rural or urban network JSON from outputs/ (rural_feeder.json or urban_feeder.json)
2. Reads outputs/h0_profile_2023.csv (columns: timestamp, load_kw or p_norm_kw)
3. Normalizes the profile if needed (p.u. relative to peak)
4. Scales load buses proportionally using pandapower ConstControl & DFData
5. Runs pandapower AC time-series power flow with OutputWriter
6. Saves results to outputs/ts_vm_pu.csv and outputs/ts_line_loading.csv
7. Prints summary statistics (min/max voltage, max line loading)
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pandapower as pp
from pandapower.control import ConstControl
from pandapower.timeseries import DFData, OutputWriter, run_timeseries


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run pandapower time-series AC power flow simulation."
    )
    parser.add_argument(
        "--network",
        type=str,
        choices=["rural", "urban"],
        default="rural",
        help="Network topology to simulate: 'rural' or 'urban' (default: rural)",
    )
    parser.add_argument(
        "--base-load",
        type=float,
        default=3.5,
        dest="base_load_kw",
        help="Base peak load per household / bus in kW (default: 3.5 kW)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        default=False,
        help="Run all timesteps (e.g. 35040 15-min steps) instead of hourly subsampling (every 4th step)",
    )
    return parser.parse_args()


def get_project_root() -> Path:
    # If script is run from src/ or project root, find the base smartgrid_ev_hp directory or current root
    script_dir = Path(__file__).resolve().parent
    if script_dir.name == "src":
        return script_dir.parent
    return Path.cwd()


def load_network(root_dir: Path, network_type: str) -> pp.pandapowerNet:
    net_file = root_dir / "outputs" / f"{network_type}_feeder.json"
    if not net_file.exists():
        raise FileNotFoundError(f"Network file not found: {net_file.resolve()}")
    print(f"[*] Loading network from: {net_file}")
    net = pp.from_json(str(net_file))
    return net


def load_and_prepare_profile(root_dir: Path, full: bool, base_load_kw: float, num_loads: int):
    profile_file = root_dir / "outputs" / "h0_profile_2023.csv"
    if not profile_file.exists():
        raise FileNotFoundError(f"Profile file not found: {profile_file.resolve()}")

    print(f"[*] Loading H0 profile from: {profile_file}")
    df = pd.read_csv(profile_file)

    # Identify timestamp column
    if "timestamp" in df.columns:
        timestamps = pd.to_datetime(df["timestamp"])
    elif "time" in df.columns:
        timestamps = pd.to_datetime(df["time"])
    elif "datetime" in df.columns:
        timestamps = pd.to_datetime(df["datetime"])
    else:
        timestamps = pd.date_range(start="2023-01-01", periods=len(df), freq="15min")

    # Identify load column (load_kw or p_norm_kw)
    if "p_norm_kw" in df.columns:
        raw_vals = df["p_norm_kw"].values
    elif "load_kw" in df.columns:
        raw_vals = df["load_kw"].values
    else:
        # Fallback to the first numeric column other than timestamp
        num_cols = df.select_dtypes(include=[np.number]).columns
        if len(num_cols) == 0:
            raise ValueError("No numeric load column found in profile CSV.")
        raw_vals = df[num_cols[0]].values

    # Normalize profile so max peak is 1.0 (p.u.)
    max_val = np.max(raw_vals)
    if max_val > 0:
        p_pu = raw_vals / max_val
    else:
        p_pu = raw_vals

    if not full:
        # Subsample to hourly (every 4th 15-min step)
        step_slice = slice(0, len(p_pu), 4)
        p_pu = p_pu[step_slice]
        timestamps = timestamps[step_slice]
        print(f"[*] Subsampling applied: 1 step every hour (total {len(p_pu)} timesteps)")
    else:
        print(f"[*] Full profile resolution used: total {len(p_pu)} timesteps")

    # Construct DataFrame for loads: scale by base_load_kw / 1000.0 (MW)
    # Each load column represents active power in MW
    p_mw_per_load = (p_pu * base_load_kw) / 1000.0  # MW
    load_df = pd.DataFrame(
        {i: p_mw_per_load for i in range(num_loads)},
        index=range(len(p_pu))
    )
    return load_df, timestamps


def main():
    args = parse_args()
    root_dir = get_project_root()
    outputs_dir = root_dir / "outputs"
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load network
    net = load_network(root_dir, args.network)
    num_loads = len(net.load)
    print(f"[*] Network '{args.network}' loaded successfully: {len(net.bus)} buses, {len(net.line)} lines, {num_loads} loads.")

    if num_loads == 0:
        raise ValueError("Network has 0 loads. Cannot run load time-series simulation.")

    # 2 & 3. Load & prepare profile
    load_df, timestamps = load_and_prepare_profile(
        root_dir=root_dir,
        full=args.full,
        base_load_kw=args.base_load_kw,
        num_loads=num_loads
    )

    # 4. Setup time-series controller
    ds = DFData(load_df)
    ConstControl(
        net,
        element="load",
        variable="p_mw",
        element_index=net.load.index,
        data_source=ds,
        profile_name=load_df.columns
    )

    # 5. Setup OutputWriter
    ow = OutputWriter(
        net,
        time_steps=range(len(load_df)),
        output_path=None,
        log_variables=[
            ("res_bus", "vm_pu"),
            ("res_line", "loading_percent")
        ]
    )

    # Run time-series AC power flow
    print(f"[*] Running AC time-series power flow for {len(load_df)} timesteps...")
    run_timeseries(net, time_steps=range(len(load_df)), verbose=False)
    print("[*] Time-series calculation completed successfully.")

    # 6. Extract and Save Results
    vm_pu_res = ow.output["res_bus.vm_pu"]
    loading_res = ow.output["res_line.loading_percent"]

    # Align indices / timestamps
    vm_pu_res.index = timestamps
    loading_res.index = timestamps

    vm_pu_file = outputs_dir / "ts_vm_pu.csv"
    loading_file = outputs_dir / "ts_line_loading.csv"

    vm_pu_res.to_csv(vm_pu_file, index_label="timestamp")
    loading_res.to_csv(loading_file, index_label="timestamp")
    print(f"[*] Bus voltage results saved to: {vm_pu_file}")
    print(f"[*] Line loading results saved to: {loading_file}")

    # 7. Print summary statistics
    min_vm = vm_pu_res.min().min()
    max_vm = vm_pu_res.max().max()
    max_loading = loading_res.max().max()

    print("\n" + "=" * 50)
    print("TIME-SERIES SIMULATION SUMMARY")
    print("=" * 50)
    print(f"Network               : {args.network}")
    print(f"Total timesteps       : {len(load_df)}")
    print(f"Base load per bus     : {args.base_load_kw:.2f} kW")
    print(f"Minimum Voltage (vm)  : {min_vm:.4f} p.u.")
    print(f"Maximum Voltage (vm)  : {max_vm:.4f} p.u.")
    print(f"Maximum Line Loading  : {max_loading:.2f} %")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()
