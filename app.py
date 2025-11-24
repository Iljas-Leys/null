# In Windows for test: ./venv/Scripts/streamlit run app.py
import datetime

import pandas as pd
import streamlit as st

from pycaret.time_series import load_model as ts_load_model, predict_model as ts_predict_model
from pycaret.regression import load_model as reg_load_model, predict_model as reg_predict_model

DEMAND_DATA_PATH = "./dataset_demanddata/cleaned_data.csv"

def strip_pkl(path: str) -> str:
    if path.lower().endswith(".pkl"):
        return path[:-4]
    return path


@st.cache_resource
def load_models():
    demand_model_path = "./dataset_demanddata/different_save_best_model.pkl"
    house_model_path = "./dataset_price_paid_records/house_price_pycaret_model.pkl"

    demand_model = ts_load_model(strip_pkl(demand_model_path))
    house_model = reg_load_model(strip_pkl(house_model_path))

    return demand_model, house_model


@st.cache_data
def load_demand_data() -> pd.DataFrame:
    df = pd.read_csv(DEMAND_DATA_PATH)
    df.columns = [c.strip().lower() for c in df.columns]
    if "year" in df.columns and "month" in df.columns:
        return df

    if "settlement_date" not in df.columns:
        raise KeyError(
            "Demand CSV must contain either 'year'/'month' or 'settlement_date'. "
            f"Found columns: {list(df.columns)}"
        )

    df["settlement_date"] = pd.to_datetime(df["settlement_date"])
    df["year"] = df["settlement_date"].dt.year
    df["month"] = df["settlement_date"].dt.month

    group_cols = ["year", "month"]
    agg_cols = [c for c in df.columns if c not in group_cols + ["settlement_date"]]

    df_monthly = (
        df.groupby(group_cols)[agg_cols]
        .mean()
        .reset_index()
    )

    return df_monthly


def build_future_exog(df_monthly: pd.DataFrame, horizon: int) -> pd.DataFrame:
    df_monthly = df_monthly.copy()
    df_monthly.columns = [c.strip().lower() for c in df_monthly.columns]

    if "year" not in df_monthly.columns or "month" not in df_monthly.columns:
        raise KeyError(
            f"'year' and/or 'month' not found in demand data columns: "
            f"{list(df_monthly.columns)}"
        )

    last = df_monthly.iloc[-1].copy()
    year = int(last["year"])
    month = int(last["month"])

    intended_exog_cols = [
        "year",
        "month",
        "nd",
        "tsd",
        "england_wales_demand",
        "embedded_wind_generation",
        "embedded_wind_capacity",
        "embedded_solar_generation",
        "embedded_solar_capacity",
        "non_bm_stor",
        "pump_storage_pumping",
        "ifa_flow",
        "britned_flow",
        "moyle_flow",
    ]

    # Only keep columns that actually exist (in case some are missing)
    exog_cols = [c for c in intended_exog_cols if c in df_monthly.columns]

    if not exog_cols:
        raise KeyError(
            "No matching exogenous columns found in demand data. "
            f"Expected some of: {intended_exog_cols}, got: {list(df_monthly.columns)}"
        )

    rows = []
    for _ in range(horizon):
        month += 1
        if month > 12:
            month = 1
            year += 1

        row = last.copy()
        row["year"] = year
        row["month"] = month
        rows.append(row[exog_cols])

    future_exog = pd.DataFrame(rows).reset_index(drop=True)
    return future_exog

st.set_page_config(page_title="PyCaret Models Demo", layout="centered")

st.title("PyCaret Inference App")
st.write(
    "This app runs inference on two trained PyCaret models:\n\n"
    "• A **time series model** for England & Wales electricity demand\n"
    "• A **regression model** for UK house prices"
)

try:
    demand_model, house_model = load_models()
except Exception as e:
    st.error(f"Error loading models: {e}")
    st.stop()

model_choice = st.sidebar.radio(
    "Choose a model",
    ["Electricity demand forecast", "House price prediction"],
)

if model_choice == "Electricity demand forecast":
    st.header("Electricity Demand Forecast")

    st.markdown(
        "This uses the trained **AutoARIMA/SARIMAX-style** model on a monthly-aggregated "
        "demand dataset (`england_wales_demand`) with **exogenous features** "
        "(nd, tsd, wind/solar, flows, ...)."
    )

    horizon = st.slider(
        "Forecast horizon (months ahead)",
        min_value=1,
        max_value=36,
        value=6,
        step=1,
    )

    if st.button("Run demand forecast"):
        try:
            df_monthly = load_demand_data()

            with st.expander("Debug: monthly demand data (tail)"):
                st.write(list(df_monthly.columns))
                st.dataframe(df_monthly.tail())

            future_exog = build_future_exog(df_monthly, horizon)

            with st.spinner("Running demand forecast with exogenous variables..."):
                forecast_df = ts_predict_model(
                    demand_model,
                    fh=horizon,
                    X=future_exog,
                )

            st.subheader("Forecast table")
            st.dataframe(forecast_df)

            numeric_cols = forecast_df.select_dtypes(include="number").columns.tolist()
            if numeric_cols:
                st.subheader("Forecast chart")
                st.line_chart(forecast_df[numeric_cols])
            else:
                st.info("No numeric columns found to plot.")

            with st.expander("Show future exogenous (X) used for forecast"):
                st.dataframe(future_exog)

        except Exception as e:
            st.error(f"Error during forecast: {e}")

elif model_choice == "House price prediction":
    st.header("House Price Prediction")

    st.markdown(
        "This uses the trained **regression model** on the UK price paid records. "
        "Fill in the fields below to estimate a property price."
    )

    with st.form("house_price_form"):
        date_of_transfer = st.date_input(
            "Date of transfer",
            value=datetime.date(2020, 1, 1),
        )

        property_type = st.selectbox(
            "Property type",
            ["Detached", "Semi-Detached", "Terraced", "Flat", "Other"],
            index=2,
        )

        old_or_new = st.selectbox(
            "Old or new",
            ["Established", "New"],
            index=0,
        )

        duration = st.selectbox(
            "Duration",
            ["Freehold", "Leasehold", "Other"],
            index=0,
        )

        town_or_city = st.text_input("Town or city", value="OLDHAM")
        district = st.text_input("District", value="OLDHAM")
        county = st.text_input("County", value="GREATER MANCHESTER")

        submitted = st.form_submit_button("Predict house price")

    if submitted:
        try:
            year = date_of_transfer.year
            month = date_of_transfer.month

            input_data = pd.DataFrame(
                [
                    {
                        "year": year,
                        "month": month,
                        "property_type": property_type,
                        "old_or_new": old_or_new,
                        "duration": duration,
                        "town_or_city": town_or_city,
                        "district": district,
                        "county": county,
                    }
                ]
            )

            pred_df = reg_predict_model(house_model, data=input_data)

            if "prediction_label" in pred_df.columns:
                predicted_price = pred_df["prediction_label"].iloc[0]
                st.success(f"Estimated price: £{predicted_price:,.0f}")
                st.caption(
                    "Note: This is an estimate based on historical data and model assumptions."
                )
            else:
                st.error(
                    "Prediction column 'prediction_label' not found in results. "
                    "Check the regression model's output."
                )

            with st.expander("Show raw prediction DataFrame"):
                st.dataframe(pred_df)

        except Exception as e:
            st.error(f"Error during house price prediction: {e}")
