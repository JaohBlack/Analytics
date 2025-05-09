import streamlit as st
import pandas as pd
import numpy as np
import joblib
import shap
import matplotlib.pyplot as plt
import seaborn as sns

# Page config
st.set_page_config(page_title="NYC Property Predictor", layout="wide")

st.title("🏙️ NYC Property Sale Price Predictor")

# Upload section
st.sidebar.header("📁 Upload NYC CSV File")
uploaded_file = st.sidebar.file_uploader("Upload your dataset (same format used for training)", type=["csv"])

# Load model
@st.cache_resource
def load_model():
    return joblib.load("model.pkl")

model = load_model()

# Preprocessing function
def preprocess(df):
    df = df.copy()

    # Handle date features
    df["SALE DATE"] = pd.to_datetime(df["SALE DATE"], errors="coerce")
    df = df[df["SALE DATE"].notna()]
    df["SALE YEAR"] = df["SALE DATE"].dt.year
    df["SALE MONTH"] = df["SALE DATE"].dt.month

    # Create building age and price per sqft
    df["BUILDING AGE"] = df["SALE YEAR"] - df["YEAR BUILT"]
    df["PRICE PER SQFT"] = df["SALE PRICE"] / df["GROSS SQUARE FEET"]

    # Create season
    def get_season(m):
        if m in [12, 1, 2]:
            return "Winter"
        elif m in [3, 4, 5]:
            return "Spring"
        elif m in [6, 7, 8]:
            return "Summer"
        else:
            return "Fall"

    df["SEASON"] = df["SALE MONTH"].apply(get_season)

    # Drop rows with missing critical values
    df = df.dropna(subset=[
        "SALE PRICE", "GROSS SQUARE FEET", "LAND SQUARE FEET",
        "BUILDING AGE", "PRICE PER SQFT", "RESIDENTIAL UNITS"
    ])

    # Encode categoricals
    categorical_cols = [
        "BOROUGH", "BUILDING CLASS CATEGORY", "SEASON", 
        "TAX CLASS AT PRESENT", "TAX CLASS AT TIME OF SALE", 
        "BUILDING CLASS AT PRESENT", "BUILDING CLASS AT TIME OF SALE"
    ]
    df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

    # Drop unused and non-numeric columns
    to_drop = [
        "SALE DATE", "ADDRESS", "NEIGHBORHOOD", "ZIP CODE", 
        "APARTMENT NUMBER", "BUILDING CLASS AT TIME OF SALE", 
        "BUILDING CLASS AT PRESENT", "EASE-MENT", "LOT", "BLOCK"
    ]
    df = df.drop([col for col in to_drop if col in df.columns], axis=1, errors='ignore')

    return df

# Main logic
if uploaded_file:
    df_raw = pd.read_csv(uploaded_file)
    st.subheader("📊 Preview of Uploaded Data")
    st.dataframe(df_raw.head())

    try:
        df_processed = preprocess(df_raw)

        X = df_processed.drop("SALE PRICE", axis=1)
        y_true = df_processed["SALE PRICE"]

        # Predict
        y_pred = model.predict(X)

        st.subheader("📈 Predicted vs Actual Sale Price")
        result_df = pd.DataFrame({
            "Actual Price": y_true,
            "Predicted Price": y_pred
        })
        st.dataframe(result_df.head(10))

        # SHAP Explanation
        st.subheader("🔍 SHAP Feature Importance")
        explainer = shap.Explainer(model)
        shap_values = explainer(X[:100])
        st.set_option("deprecation.showPyplotGlobalUse", False)
        shap.summary_plot(shap_values, X.iloc[:100], show=False)
        st.pyplot()

        # Borough-level visualization (if column available)
        if "BOROUGH" in df_raw.columns:
            st.subheader("📍 Average Sale Price by Borough")
            borough_avg = df_raw.groupby("BOROUGH")["SALE PRICE"].mean().reset_index()
            fig, ax = plt.subplots(figsize=(8, 5))
            sns.barplot(data=borough_avg, x="BOROUGH", y="SALE PRICE", ax=ax)
            ax.set_ylabel("Average Sale Price")
            st.pyplot(fig)

    except Exception as e:
        st.error(f"❌ An error occurred during prediction: {e}")
else:
    st.info("👈 Please upload a CSV file to begin.")
