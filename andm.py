import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import requests
from pathlib import Path
from datetime import timedelta
from functools import reduce

st.set_page_config(layout="wide")

# Hashid
target_hashes = [
    "9e9dca492a061e211740838882",
    "3fd0482ebd211dd11741080835",
    "ed9f4fcf0bfb1afa1741424674",
    "c550bcace2429c281741504217",
    "d8cd1b7c670501c41742115495",
    "6f9be12993e8e64a1742388290",
    "eb18877694cc036a1742320408",
    "ed2284e75ccc65c31743346721",
    "9b14faeebab3210c1744226116",
    "aa9c3ce25421e6231742320435"
]

# Allalaadimise kataloog
download_dir = Path("data")
download_dir.mkdir(parents=True, exist_ok=True)


# Andmete allalaadimine (ainult kui faili pole)
def download_data():
    for h in target_hashes:
        file_path = download_dir / f"{h}.csv"
        if not file_path.exists():
            url = f"https://decision.cs.taltech.ee/electricity/data/{h}.csv"
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    file_path.write_bytes(response.content)
                    print(f"✓ Laaditud: {file_path.name}")
                else:
                    print(f"✗ HTTP {response.status_code} — {file_path.name}")
            except Exception as e:
                print(f"✗ Viga ühendusel {file_path.name}: {e}")


download_data()


# Funktsioonid
def find_100_day_window(dates):
    dates = sorted(list(set(dates)))
    for i in range(len(dates) - 99):
        window = dates[i:i+100]
        expected = [window[0] + timedelta(days=j) for j in range(100)]
        if window == expected:
            return window
    return None


@st.cache_data
def load_and_process_first_dataset():
    h = target_hashes[0]
    df = pd.read_csv(download_dir / f"{h}.csv", sep=';', skiprows=4)
    df.columns = ['Periood', 'consumption']
    df['Periood'] = pd.to_datetime(df['Periood'], dayfirst=True, errors='coerce')
    df['consumption'] = df['consumption'].astype(str).str.replace(',', '.').astype(float)
    df.dropna(subset=['Periood'], inplace=True)
    df['date'] = df['Periood'].dt.date
    df['hour'] = df['Periood'].dt.hour

    pivot = df.pivot_table(index='date', columns='hour', values='consumption')
    pivot = pivot.dropna()
    dates = pivot.index
    valid_window = find_100_day_window(dates)

    if not valid_window:
        st.error("Ei leitud 100 järjestikust täielikku päeva.")
        return None

    return pivot.loc[valid_window]


@st.cache_data
def find_common_day():
    all_dates = []
    for h in target_hashes[:10]:
        df = pd.read_csv(download_dir / f"{h}.csv", sep=';', skiprows=4)
        df.columns = ['Periood', 'consumption']
        df['Periood'] = pd.to_datetime(df['Periood'], dayfirst=True, errors='coerce')
        df.dropna(subset=['Periood'], inplace=True)
        df['date'] = df['Periood'].dt.date
        all_dates.append(set(df['date']))
    common_dates = sorted(reduce(lambda a, b: a & b, all_dates))
    return common_dates[0] if common_dates else None


@st.cache_data
def load_day_data(common_day):
    data = {}
    for h in target_hashes[:10]:
        df = pd.read_csv(download_dir / f"{h}.csv", sep=';', skiprows=4)
        df.columns = ['Periood', 'consumption']
        df['Periood'] = pd.to_datetime(df['Periood'], dayfirst=True, errors='coerce')
        df.dropna(subset=['Periood'], inplace=True)
        df['consumption'] = df['consumption'].astype(str).str.replace(',', '.').astype(float)
        df['date'] = df['Periood'].dt.date
        df['hour'] = df['Periood'].dt.hour
        df_day = df[df['date'] == common_day]
        data[h[-4:]] = df_day
    return data


# Streamlit UI
st.title("Elektritarbimise visualiseerimine")

st.subheader("Ülesanne 1: Heatmap 100 järjestikusest päevast")
pivot = load_and_process_first_dataset()
if pivot is not None:
    fig1, ax1 = plt.subplots(figsize=(14, 8))
    sns.heatmap(pivot, cmap="YlGnBu", ax=ax1)
    ax1.set_title("Tarbimine 100 päeva jooksul")
    ax1.set_xlabel("Tund")
    ax1.set_ylabel("Kuupäev")
    st.pyplot(fig1)

st.subheader("Ülesanne 2: Ühe päeva võrdlus graafikul")
common_day = find_common_day()
if common_day:
    day_data = load_day_data(common_day)
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    for label, df in day_data.items():
        if not df.empty:
            ax2.plot(df['hour'], df['consumption'], label=label)
    ax2.legend(title="Mõõtepunkt")
    ax2.set_title(f"Tarbimine kuupäeval {common_day}")
    ax2.set_xlabel("Tund")
    ax2.set_ylabel("kWh")
    ax2.grid(True)
    st.pyplot(fig2)
else:
    st.error("Ühist kuupäeva ei leitud.")
