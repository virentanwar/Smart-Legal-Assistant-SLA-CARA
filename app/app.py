#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr 15 21:03:28 2025

@author: shashankgandavarapu
"""

import gradio as gr
from pprint import pprint
import pandas as pd
from sla_cara_pipeline import run_pipeline

def format_text_for_table(text):
    return text.replace("**", "").replace("-", "•").replace("\n", " ").strip()
import json
import re

def format_summary(summary_raw):
    """
    Extracts the 'summary' value from a JSON string or returns the original text if parsing fails.
    """
    try:
        parsed = json.loads(summary_raw)
        return parsed.get("summary", summary_raw)
    except Exception:
        return summary_raw 
def safe_json_parse(raw):
    """
    Attempts to parse a JSON string, falling back to the raw string on failure.
    """
    try:
        return json.loads(raw)
    except Exception:
        return raw
    
def format_classification(classification_raw):
    parsed = safe_json_parse(classification_raw)
    if isinstance(parsed, dict):
        return f"{parsed.get('Category', '')}: {parsed.get('Reasoning', '')}"
    return classification_raw

def format_legal_extraction(raw_text):
    """
    Safely formats the legal_extraction text into a human-readable string,
    handling JSON, pseudo-dict, or fallback raw text.
    """
    if not raw_text:
        return ""
    
    try:
        # Try to parse as strict JSON
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        try:
            # Fix common non-JSON issues like sets used as values
            fixed = re.sub(r'{\s*([^:]+?)\s*}', r'["\1"]', raw_text)  # sets -> lists
            fixed = re.sub(r'(\w+)\s*:', r'"\1":', fixed)             # unquoted keys
            data = json.loads(fixed)
        except Exception:
            return raw_text  # fallback to showing raw string
    
    parts = []
    for key, value in data.items():
        if isinstance(value, (list, set)):
            val_str = ", ".join(str(v) for v in value if v)
        elif isinstance(value, dict):
            val_str = ", ".join(str(v) for v in value.values() if v)
        else:
            val_str = str(value)
        if val_str:
            parts.append(f"{key}: {val_str}")
    return " | ".join(parts)


def process_file(file_obj):
    try:
        result = run_pipeline(file_obj, is_file=True)
        if isinstance(result, list):
            rows = []
            for i, r in enumerate(result):
                row = {
                    "Clause ID": i,
                    "Clause": r.get("clause", ""),
                    "Classification": format_text_for_table(r.get("classification", "")),
                    "Risk Score": r.get("risk_analysis", {}).get("Risk Score") if r.get("risk_analysis") else None,
                    "Legal Risks": ", ".join(r.get("risk_analysis", {}).get("Legal Risks", [])) if r.get("risk_analysis") else None,
                    "Summary": format_summary(r.get("summary", "")),
                    "Legal Extraction": format_legal_extraction(r.get("legal_extraction", ""))

                }
                rows.append(row)
            df = pd.DataFrame(rows)
            return df
        else:
            return pd.DataFrame([{"Error": "Expected list of clauses from contract"}])
    except Exception as e:
        return pd.DataFrame([{"Error": str(e)}])


def process_clause(clause_text):
    try:
        r = run_pipeline(clause_text, is_file=False)
        df = pd.DataFrame([{
            "Clause ID": 0,
            "Clause": r.get("clause", ""),
            "Classification": format_classification(r.get("classification", "")),
            "Risk Score": r.get("risk_analysis", {}).get("Risk Score") if r.get("risk_analysis") else None,
            "Legal Risks": ", ".join(r.get("risk_analysis", {}).get("Legal Risks", [])) if r.get("risk_analysis") else None,
            "Summary": format_summary(r.get("summary", "")),
            "Legal Extraction": format_legal_extraction(r.get("legal_extraction", ""))

        }])
        return df
    except Exception as e:
        return pd.DataFrame([{"Error": str(e)}])

with gr.Blocks() as demo:
    gr.Markdown("# 🤖 Smart Legal Assistant – Contract Analysis and Risk Assessment (SLA-CARA)")
    gr.Markdown("Upload a PDF or paste a legal clause to analyze classification, risks, and summary.")
    headers = ["Clause ID", "Clause", "Classification", "Risk Score", "Legal Risks", "Summary", "Legal Extraction"]
    with gr.Tab("📄 Upload Full Contract (PDF)"):
        file_input = gr.File(label="Upload Contract (PDF)", file_types=[".pdf", ".PDF"])
        
        contract_output = gr.Dataframe(label="Clause Analysis Table", headers=headers, wrap=True, datatype=["number", "str", "str", "number", "str", "str", "str"])
        file_analyze_btn = gr.Button("Analyze Contract")
        file_analyze_btn.click(fn=process_file, inputs=file_input, outputs=contract_output)

    with gr.Tab("✍️ Analyze a Single Clause"):
        clause_input = gr.Textbox(lines=8, label="Paste a Legal Clause")
        clause_output = gr.Dataframe(label="Clause Analysis Table", headers=headers, wrap=True, datatype=["number", "str", "str", "number", "str", "str", "str"])
        clause_analyze_btn = gr.Button("Analyze Clause")
        clause_analyze_btn.click(fn=process_clause, inputs=clause_input, outputs=clause_output)

demo.launch()