import pandas as pd
from datetime import datetime
import streamlit as st

def load_data(file_obj):
    """
    Loads data from a file-like object into a pandas DataFrame.
    """
    try:
        return pd.read_csv(file_obj)
    except Exception as e:
        st.error(f"Failed to load CSV data: {e}")
        return pd.DataFrame()

def enrich_dataframe(df, config):
    """
    Enriches the raw dataframe with calculated scores based on the config.
    """
    # Safely get column_mapping and rename columns
    column_mapping = config.get('column_mapping', {})
    if isinstance(column_mapping, dict):
        df = df.rename(columns=column_mapping)
    else:
        st.warning("Config Warning: `column_mapping` in config.yaml is not formatted correctly.")

    # Calculate Days_Since_Connection if 'Connected_On' column exists
    if 'Connected_On' in df.columns:
        df['Connected_On'] = pd.to_datetime(df['Connected_On'], errors='coerce')
        df['Days_Since_Connection'] = (datetime.now() - df['Connected_On']).dt.days
    
    # --- Trust Score Calculation ---
    trust_params = config.get('trust_score_parameters', {})
    weights = {}
    if isinstance(trust_params, dict):
        weights = trust_params.get('weights', {})
    else:
        st.warning("Config Warning: `trust_score_parameters` in config.yaml is not a valid section.")

    df['Trust_Score'] = 0
    
    if isinstance(weights, dict) and weights:
        for param, weight in weights.items():
            if param in df.columns:
                df[param] = pd.to_numeric(df[param], errors='coerce').fillna(0)
                max_val = df[param].max()
                if max_val > 0:
                    # --- PATCH START: Restored Recency Scoring Logic ---
                    # Special handling for 'recency' scores where a lower value is better.
                    if param == 'Days_Since_Connection':
                        # This inverts the score, giving the highest score to the newest connection.
                        normalized_score = ((max_val - df[param]) / max_val) * 100
                    else:
                        # Standard normalization for scores where a higher value is better.
                        normalized_score = (df[param] / max_val) * 100
                    # --- PATCH END ---
                    
                    df['Trust_Score'] += normalized_score * weight
            else:
                # This warning helps debug config/data mismatches
                st.warning(f"Config Warning: The column '{param}' used for scoring in `trust_score_parameters` was not found in your data.")
    else:
        st.warning("Config Warning: `trust_score_parameters.weights` in config.yaml is missing or not formatted correctly. Trust Score may be 0.")

    return df
