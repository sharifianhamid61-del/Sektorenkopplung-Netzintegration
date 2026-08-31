# Sektorenkopplung & Smart Grid Integration (§14a EnWG)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![pandapower](https://img.shields.io/badge/Power_System-pandapower-orange.svg)](https://www.pandapower.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 📌 Project Overview
This repository provides a complete quasi-dynamic time-series simulation framework for low-voltage (LV) and medium-voltage (MV) distribution networks integrating sector coupling technologies: **Photovoltaic (PV) systems, Battery Energy Storage Systems (BESS), Electric Vehicle (EV) chargers, and Heat Pumps (HP)**.

The framework benchmarks uncontrolled integration scenarios against intelligent flexibility management under the German regulatory framework (**§14a EnWG**), resolving grid bottlenecks (thermal line overloading and voltage band violations).

---

## 🚀 Key Features

* **Quasi-Dynamic Time-Series Power Flow:** 24-hour simulation with 15-minute resolution (96 time steps) using `pandapower`.
* **Sector Coupling Assets:** Dynamic modelling of simultaneous residential loads, EV home charging ($11\,\text{kW}$), Heat Pump thermal cycles, and distributed rooftop PV generation.
* **§14a EnWG Flexibility Management:** Implementation of smart curtailment and peak-shaving dimming algorithms for controllable consumption units (*SteuVE*).
* **Grid Impact & Bottleneck Analysis:** Automated evaluation of line loading rates ($\%$) and nodal voltage profiles ($U/U_n$).
* **Visual Performance Reporting:** Comparative Before/After plots highlighting grid relief and capacity optimization.

---

## 🛠️ Tech Stack & Dependencies

* **Language:** Python 3.10+
* **Core Libraries:**
  * `pandapower` — Power system load flow and time-series analysis
  * `pandas` & `numpy` — Profile synthesis and data manipulation
  * `matplotlib` & `seaborn` — Visualization and report generation

---

## 📂 Project Structure
```text
├── data/
│   ├── load_profiles/         # Synthesized standard & dynamic profiles (H0, P_EV, P_HP, PV)
│   └── grid_models/           # Benchmark grid topology / pandapower JSON models
├── src/
│   ├── 01_grid_builder.py     # Grid topology definition
│   ├── 04_bess_strategy.py    # Battery storage control logic
│   ├── 08_time_series_analysis.py # 24h quasi-dynamic simulation & §14a EnWG logic
│   └── utils_plot.py          # Visualization utilities
├── results/
│   ├── voltage_profiles.png   # Voltage band comparison (Uncontrolled vs Controlled)
│   └── line_loading.png       # Thermal line capacity comparison
├── README.md
├── requirements.txt
└── LICENSE

---

## 📊 Methodology & Workflow

1. **Baseline Load Profile Synthesis:** Modeling synchronous peak demands (e.g., evening residential demand + simultaneous EV charging at 19:45).
2. **Uncontrolled Scenario ($H_1$):** Demonstrating voltage drop violations ($U < 0.90\,\text{p.u.}$) and feeder line overload ($> 100\,\%$) under high penetration.
3. **Flexibility Activation ($H_2$ under §14a EnWG):** Dynamic load throttling of controllable units to preserve grid stability without unnecessary energy curtailment.

---

## ⚡ Quick Start

### 1. Clone the Repository
bash
git clone https://github.com/sharifianhamid61-del/Sektorenkopplung-Netzintegration.git
cd Sektorenkopplung-Netzintegration

### 2. Set Up Virtual Environment
bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

### 3. Run Time-Series Simulation
bash
python src/08_time_series_analysis.py

---

👨‍💻 Autor
Hamid Sharifian

M.Sc. Electrical Power Engineer | Experte für Power Grid Analytics & Geospatial Analysis

💼 [LinkedIn Profil](https://linkedin.com/in/hamid-sharifian-4b349052)
🎓 [Google Scholar](https://scholar.google.com/citations?user=PsIZ3g50uOAAAAJ)
📧 sharifian.hamid61@gmail.com
