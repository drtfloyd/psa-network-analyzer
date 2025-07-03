import pandas as pd
import streamlit as st

def evaluate_connections(df, config):
    """
    Calculates the final Composite Score, Recommended Action, and Persona Tags.
    """
    composite_weights = config.get('composite_score_weights', {})
    df['Composite_Score'] = 0
    
    if isinstance(composite_weights, dict) and composite_weights:
        for score_component, weight in composite_weights.items():
            if score_component in df.columns:
                df[score_component] = pd.to_numeric(df[score_component], errors='coerce').fillna(0)
                df['Composite_Score'] += df[score_component] * weight
    else:
        st.warning("Config Warning: `composite_score_weights` in config.yaml is missing or not formatted correctly. Composite Score will be 0.")

    thresholds = config.get('thresholds', {})
    labels = config.get('action_labels', {})
    
    def get_action_tier(score):
        if isinstance(thresholds, dict):
            for tier, limit in sorted(thresholds.items(), key=lambda item: item[1], reverse=True):
                if score >= limit:
                    return labels.get(tier, tier.title())
        return labels.get('withdraw', 'Withdraw')

    df['Recommended_Action'] = df['Composite_Score'].apply(get_action_tier)

    persona_rules = config.get('persona_rules', {})
    
    def get_persona_tags(row):
        tags = []
        if isinstance(persona_rules, dict):
            for tag, rules in persona_rules.items():
                if not isinstance(rules, list): continue
                conditions_met = True
                for condition in rules:
                    if not isinstance(condition, dict):
                        conditions_met = False; break
                    col = condition.get('column')
                    op = condition.get('operator')
                    val = condition.get('value')
                    
                    if col not in row or pd.isna(row[col]):
                        conditions_met = False; break
                    
                    if op == '>=' and not (row[col] >= val): conditions_met = False
                    elif op == '<=' and not (row[col] <= val): conditions_met = False
                    elif op == '>' and not (row[col] > val): conditions_met = False
                    elif op == '<' and not (row[col] < val): conditions_met = False
                    elif op == '==' and not (row[col] == val): conditions_met = False
                    elif op == 'in' and str(val).lower() not in str(row[col]).lower(): conditions_met = False
                    
                    if not conditions_met: break
                if conditions_met: tags.append(tag)
        return ', '.join(tags) if tags else 'N/A'

    df['Persona_Tags'] = df.apply(get_persona_tags, axis=1)
    
    return df.sort_values(by='Composite_Score', ascending=False)
