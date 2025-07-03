import streamlit as st
import yaml
import os
import io

# Import the refactored processing functions from your other files
from preprocess_scores import enrich_dataframe, load_data
from psa_network_evaluator import evaluate_connections

# --- Page Configuration ---
st.set_page_config(
    page_title="PSA Network Analyzer™",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Constants & File Paths ---
CONFIG_FILE = "config.yaml"
SAMPLE_INPUT_FILE = "sample_input.csv"

# --- Cached Functions for Performance ---

@st.cache_data(show_spinner="Loading configuration...")
def load_app_config(config_path):
    """Loads the YAML config file, with error handling."""
    if not os.path.exists(config_path):
        st.error(f"Configuration Error: '{config_path}' not found. Please ensure it exists in the application's root directory.")
        st.stop()
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        st.error(f"Configuration Error: Invalid YAML format in '{config_path}': {e}")
        st.stop()

@st.cache_data(show_spinner="Processing your connections data...")
def run_evaluation_pipeline(uploaded_file_obj, config):
    """Runs the full data processing pipeline."""
    try:
        df_raw = load_data(uploaded_file_obj)
        if df_raw.empty:
            st.warning("The uploaded CSV file is empty. Please upload a file with data.")
            return None, "empty_file"

        st.info(f"Loaded {len(df_raw)} connections. Now enriching and evaluating...")
        
        # Use the imported functions to process the data
        df_enriched = enrich_dataframe(df_raw.copy(), config)
        df_final = evaluate_connections(df_enriched.copy(), config)

        st.success("✅ Network evaluation complete!")
        return df_final, "success"
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        st.info("Please verify your input CSV format and `config.yaml` settings.")
        return None, "unexpected_error"


# --- Main Streamlit App Layout ---

st.title("🤝 PSA Network Analyzer™")
st.markdown("Optimize your professional network by gaining **transparent, actionable insights** into your connections.")

# --- Sidebar for Controls and Info ---
with st.sidebar:
    st.header("1. Upload Your Data")
    uploaded_file = st.file_uploader(
        "Upload your LinkedIn/CRM Connections CSV",
        type=["csv"],
        help=f"Ensure your CSV contains all columns needed by your '{CONFIG_FILE}'."
    )
    st.markdown("---")
    st.write("Or use a sample dataset:")
    if os.path.exists(SAMPLE_INPUT_FILE):
        if st.button("Load Sample Data", help=f"Loads '{SAMPLE_INPUT_FILE}' for demonstration."):
            with open(SAMPLE_INPUT_FILE, "rb") as f:
                st.session_state['sample_file_loaded'] = io.BytesIO(f.read())
                st.session_state['sample_file_loaded'].name = SAMPLE_INPUT_FILE
            if 'user_uploaded_file' in st.session_state:
                del st.session_state['user_uploaded_file']
            st.rerun()
    else:
        st.warning(f"Sample file '{SAMPLE_INPUT_FILE}' not found.")
    st.header("2. Configuration")
    st.info(f"Using configuration from: `{CONFIG_FILE}`.")
    config = load_app_config(CONFIG_FILE)
    st.markdown("---")
    st.caption("Powered by Presence Signaling Architecture™")

if uploaded_file:
    st.session_state['user_uploaded_file'] = uploaded_file

# --- Main Content Area ---
current_file_in_session = st.session_state.get('user_uploaded_file') or st.session_state.get('sample_file_loaded')

if current_file_in_session:
    final_ranked_df, status = run_evaluation_pipeline(current_file_in_session, config)
    if status == "success" and final_ranked_df is not None:
        st.header("📊 Network Evaluation Results")
        st.subheader("1. Ranked Connections Overview")
        st.markdown("Your connections, sorted by **Composite Score** and assigned an **Action Recommendation**.")
        action_labels_map = config.get("action_labels", {})
        color_map = {
            action_labels_map.get("keep", "Keep"): "#66BB6A",
            action_labels_map.get("cultivate", "Cultivate"): "#FFA726",
            action_labels_map.get("nurture", "Nurture"): "#FFCA28",
            action_labels_map.get("monitor", "Monitor"): "#FFEE58",
            action_labels_map.get("withdraw", "Withdraw"): "#EF5350"
        }
        def color_action_tiers(val):
            return f'background-color: {color_map.get(val, "white")}'
        
        display_columns = [
            'First Name', 'Last Name', 'Company', 'Position', 
            'Composite_Score', 'Recommended_Action', 'Persona_Tags', 'Trust_Score'
        ]
        
        existing_display_columns = [col for col in display_columns if col in final_ranked_df.columns]
        other_columns = [col for col in final_ranked_df.columns if col not in existing_display_columns]
        final_columns_order = existing_display_columns + other_columns
        
        display_df = final_ranked_df[final_columns_order]
        
        styled_df = display_df.style.applymap(color_action_tiers, subset=['Recommended_Action'])
        st.dataframe(styled_df, use_container_width=True)

        st.subheader("2. Recommended Actions Breakdown")
        ordered_actions = [action_labels_map.get(key, key.title()) for key in config.get("thresholds", {}).keys()]
        action_counts = final_ranked_df["Recommended_Action"].value_counts().reindex(ordered_actions).fillna(0)
        st.bar_chart(action_counts)

        st.subheader("3. Persona Tags Breakdown")
        all_tags = final_ranked_df["Persona_Tags"].str.split(', ').explode().dropna()
        all_tags = all_tags[all_tags != 'N/A'].str.strip()
        if not all_tags.empty:
            tag_counts = all_tags.value_counts().sort_index()
            st.bar_chart(tag_counts)
        else:
            st.info("No persona tags were assigned based on current rules.")

        st.subheader("4. Data Preview (with Scores & Tags)")
        st.dataframe(final_ranked_df.head(), use_container_width=True)

        st.download_button(label="💾 Download Full Evaluated Connections CSV", data=final_ranked_df.to_csv(index=False).encode('utf-8'), file_name="PSA_Ranked_Connections.csv", mime="text/csv")

else:
    st.info("Please upload a CSV file or load sample data using the sidebar to begin.")
