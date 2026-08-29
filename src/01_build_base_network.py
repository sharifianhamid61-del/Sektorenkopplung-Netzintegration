import sys
from pathlib import Path
import pandapower as pp
import pandapower.networks as pn

output_dir = Path(__file__).resolve().parent.parent / "outputs"
output_dir.mkdir(parents=True, exist_ok=True)

networks = {}
source_type = ""

try:
    import simbench as sb
    net_rural = sb.get_simbench_net("1-LV-rural1--0-no_sw")
    net_urban = sb.get_simbench_net("1-LV-urban6--0-no_sw")
    networks["rural"] = net_rural
    networks["urban"] = net_urban
    source_type = "simbench"
except Exception as e:
    net_rural = pn.create_kerber_landnetz_kabel_1()
    net_urban = pn.create_kerber_vorstadtnetz_kabel_2()
    networks["rural"] = net_rural
    networks["urban"] = net_urban
    source_type = f"pandapower.networks Kerber benchmark (fallback due to: {type(e).__name__})"

print(f"Network source used: {source_type}" + "\n" + "=" * 50)

for name, net in networks.items():
    print("\n--- Diagnostics for " + name.upper() + " Network ---")
    print(f"Buses:        {len(net.bus)}")
    print(f"Lines:        {len(net.line)}")
    print(f"Loads:        {len(net.load)}")
    print(f"Transformers: {len(net.trafo)}")

    pp.runpp(net)
    v_min = net.res_bus.vm_pu.min()
    v_max = net.res_bus.vm_pu.max()
    print("Power Flow:   CONVERGED")
    print(f"Min Voltage:  {v_min:.4f} p.u.")
    print(f"Max Voltage:  {v_max:.4f} p.u.")

    out_file = output_dir / f"{name}_feeder.json"
    pp.to_json(net, str(out_file))
    print(f"Saved to:     {out_file.resolve()} (Size: {out_file.stat().st_size:,} bytes)")

print("\n" + "=" * 50)
print("Step 1 successfully completed.")
