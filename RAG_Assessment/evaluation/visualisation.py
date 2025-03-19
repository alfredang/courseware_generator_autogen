import os
import sys
import json
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from typing import Dict, Any, List, Optional

def create_retrieval_visualizations(retrieval_results: Dict[str, Any]) -> Dict[str, go.Figure]:
    """Create visualizations for retrieval quality evaluation results."""
    figures = {}
    summary = retrieval_results.get("summary", {})
    learning_units = retrieval_results.get("learning_units", {})
    
    # 1. Relevance distribution histogram
    if learning_units:
        all_relevance_scores = []
        for lu_data in learning_units.values():
            for source in lu_data.get("source_details", []):
                all_relevance_scores.append(source.get("relevance", 0))
        
        if all_relevance_scores:
            fig = px.histogram(
                x=all_relevance_scores,
                nbins=20,
                title="Distribution of Document Relevance Scores",
                labels={"x": "Relevance Score", "y": "Count"},
                color_discrete_sequence=["#3366cc"]
            )
            fig.add_vline(x=np.mean(all_relevance_scores), line_dash="dash", line_color="red", 
                         annotation_text=f"Mean: {np.mean(all_relevance_scores):.2f}")
            figures["relevance_distribution"] = fig
    
    # 2. Information Density vs. Relevance scatter plot
    if learning_units:
        relevance_scores = []
        info_density_scores = []
        text_previews = []
        unit_names = []
        
        for lu_name, lu_data in learning_units.items():
            for source in lu_data.get("source_details", []):
                relevance_scores.append(source.get("relevance", 0))
                info_density_scores.append(source.get("info_density", 0))
                text_previews.append(source.get("text_preview", ""))
                unit_names.append(lu_name)
        
        if relevance_scores and info_density_scores:
            df = pd.DataFrame({
                "Relevance": relevance_scores,
                "Info Density": info_density_scores,
                "Preview": text_previews,
                "Learning Unit": unit_names
            })
            
            fig = px.scatter(
                df, x="Relevance", y="Info Density", 
                color="Learning Unit", hover_data=["Preview"],
                title="Information Density vs. Relevance",
                labels={"Relevance": "Relevance Score", "Info Density": "Information Density Score"}
            )
            figures["relevance_vs_density"] = fig
    
    # 3. Average metrics by learning unit
    if learning_units:
        lu_names = list(learning_units.keys())
        avg_relevance = [lu.get("avg_relevance", 0) for lu in learning_units.values()]
        avg_density = [lu.get("avg_info_density", 0) for lu in learning_units.values()]
        source_counts = [lu.get("sources_count", 0) for lu in learning_units.values()]
        
        # Sort by relevance score
        sorted_indices = np.argsort(avg_relevance)
        lu_names = [lu_names[i] for i in sorted_indices]
        avg_relevance = [avg_relevance[i] for i in sorted_indices]
        avg_density = [avg_density[i] for i in sorted_indices]
        source_counts = [source_counts[i] for i in sorted_indices]
        
        # Create figure with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add traces
        fig.add_trace(
            go.Bar(x=lu_names, y=avg_relevance, name="Avg. Relevance", marker_color="#3366cc"),
            secondary_y=False,
        )
        
        fig.add_trace(
            go.Bar(x=lu_names, y=avg_density, name="Avg. Info Density", marker_color="#dc3912"),
            secondary_y=False,
        )
        
        fig.add_trace(
            go.Scatter(x=lu_names, y=source_counts, name="Source Count", mode="markers", marker_color="#ff9900"),
            secondary_y=True,
        )
        
        # Set titles
        fig.update_layout(title_text="Retrieval Performance by Learning Unit")
        fig.update_xaxes(title_text="Learning Unit", tickangle=45)
        fig.update_yaxes(title_text="Score", secondary_y=False)
        fig.update_yaxes(title_text="Number of Sources", secondary_y=True)
        
        figures["metrics_by_unit"] = fig
    
    # 4. Summary radar chart
    if summary:
        categories = ["Relevance", "Information Density", "Source Count", "Content Length"]
        values = [
            summary.get("avg_relevance", 0) * 10,  # Scale to 0-10
            summary.get("avg_info_density", 0) * 10,
            min(summary.get("avg_source_count", 0) / 5, 1.0) * 10,  # Normalize to 0-10
            min(summary.get("avg_source_length", 0) / 2000, 1.0) * 10  # Normalize to 0-10
        ]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name='Retrieval Metrics'
        ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 10]
                )),
            showlegend=False,
            title="Retrieval Quality Summary"
        )
        
        figures["summary_radar"] = fig
    
    return figures

def create_assessment_visualizations(assessment_results: Dict[str, Any]) -> Dict[str, go.Figure]:
    """Create visualizations for educational assessment quality results."""
    figures = {}
    summary = assessment_results.get("summary", {})
    
    # 1. Bloom's Taxonomy Distribution
    bloom_distribution = summary.get("bloom_distribution", {})
    if bloom_distribution:
        levels = list(bloom_distribution.keys())
        values = list(bloom_distribution.values())
        
        # Sort by cognitive complexity (remember->create)
        cognitive_order = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
        sorted_indices = [cognitive_order.index(level) for level in levels]
        levels = [levels[i] for i in np.argsort(sorted_indices)]
        values = [values[i] for i in np.argsort(sorted_indices)]
        
        colors = px.colors.sequential.Viridis[:len(levels)]
        
        fig = go.Figure(data=[go.Bar(
            x=levels,
            y=values,
            marker_color=colors,
            text=[f"{v:.1%}" for v in values],
            textposition='auto',
        )])
        
        fig.update_layout(
            title="Distribution of Questions by Bloom's Taxonomy Level",
            xaxis_title="Cognitive Level",
            yaxis_title="Proportion of Questions",
            yaxis_tickformat='.0%',
        )
        
        figures["blooms_distribution"] = fig
    
    # 2. Question Type Distribution
    question_types = summary.get("question_type_distribution", {})
    if question_types:
        types = list(question_types.keys())
        values = list(question_types.values())
        
        fig = px.pie(
            names=types, 
            values=values, 
            title="Question Type Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        
        fig.update_traces(textposition='inside', textinfo='percent+label')
        figures["question_types"] = fig
    
    # 3. Questions Per Unit Distribution
    questions_per_unit = assessment_results.get("learning_units", {})
    if questions_per_unit:
        unit_names = list(questions_per_unit.keys())
        # Count total questions in each unit
        question_counts = []
        bloom_levels_by_unit = []
        
        for unit_data in questions_per_unit.values():
            bloom_counts = unit_data.get("bloom_levels", {})
            total = sum(bloom_counts.values())
            question_counts.append(total)
            
            # Get the most frequent Bloom's level
            if bloom_counts:
                max_level = max(bloom_counts, key=bloom_counts.get)
                bloom_levels_by_unit.append(max_level)
            else:
                bloom_levels_by_unit.append("unknown")
        
        # Sort by question count
        sorted_indices = np.argsort(question_counts)[::-1]  # Descending
        unit_names = [unit_names[i] for i in sorted_indices]
        question_counts = [question_counts[i] for i in sorted_indices]
        bloom_levels_by_unit = [bloom_levels_by_unit[i] for i in sorted_indices]
        
        fig = px.bar(
            x=unit_names, 
            y=question_counts,
            color=bloom_levels_by_unit,
            labels={"x": "Learning Unit", "y": "Number of Questions", "color": "Predominant Bloom's Level"},
            title="Questions Per Learning Unit",
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        
        fig.update_xaxes(tickangle=45)
        figures["questions_per_unit"] = fig
    
    return figures

def create_ablation_visualizations(ablation_results: Dict[str, Any]) -> Dict[str, go.Figure]:
    """Create visualizations for ablation study results."""
    figures = {}
    
    # Extract results for each configuration
    config_names = list(ablation_results.keys())
    if not config_names:
        return figures
    
    # 1. Overall performance comparison
    metrics = {}
    for config_name, result in ablation_results.items():
        # Extract the metrics from the result
        if "avg_source_count" in result:
            if "source_count" not in metrics:
                metrics["source_count"] = []
            metrics["source_count"].append(result["avg_source_count"])
            
        # Extract more metrics as needed
    
    if metrics:
        # Create a DataFrame for visualization
        df = pd.DataFrame({
            "Configuration": config_names,
            **{metric: values for metric, values in metrics.items()}
        })
        
        # Melt the DataFrame for easier plotting
        df_melted = pd.melt(
            df, 
            id_vars=["Configuration"], 
            var_name="Metric", 
            value_name="Value"
        )
        
        fig = px.bar(
            df_melted,
            x="Configuration", 
            y="Value", 
            color="Metric",
            barmode="group",
            title="Performance Comparison Across Configurations",
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        
        figures["ablation_comparison"] = fig
    
    # 2. Detailed comparison as radar chart
    if "baseline" in ablation_results and ablation_results["baseline"].get("unit_results"):
        # Get all available metrics from the first unit result
        first_config = next(iter(ablation_results.values()))
        first_unit = next(iter(first_config.get("unit_results", {}).values()))
        metric_names = list(first_unit.keys())
        
        # Create a radar chart comparing configurations
        fig = go.Figure()
        
        for config_name, result in ablation_results.items():
            # Average metrics across all units
            avg_metrics = {}
            for metric in metric_names:
                values = [u.get(metric, 0) for u in result.get("unit_results", {}).values()]
                if values:
                    avg_metrics[metric] = sum(values) / len(values)
            
            # Normalize values for radar chart
            max_values = {
                metric: max(
                    max(
                        u.get(metric, 0) for u in c.get("unit_results", {}).values()
                    ) 
                    for c in ablation_results.values()
                ) 
                for metric in metric_names
            }
            
            normalized_values = [
                avg_metrics.get(metric, 0) / (max_values.get(metric, 1) or 1)  # Avoid division by zero
                for metric in metric_names
            ]
            
            fig.add_trace(go.Scatterpolar(
                r=normalized_values,
                theta=metric_names,
                fill='toself',
                name=config_name
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1]
                )),
            title="Configuration Performance Comparison"
        )
        
        figures["ablation_radar"] = fig
        
    return figures

def create_evaluation_report(results: Dict[str, Any], output_file: str = "evaluation_report.html"):
    """Generate a comprehensive HTML evaluation report with all visualizations."""
    # Create all visualizations
    retrieval_figures = create_retrieval_visualizations(results.get("retrieval", {}))
    assessment_figures = create_assessment_visualizations(results.get("assessment", {}))
    ablation_figures = create_ablation_visualizations(results.get("ablation", {}))
    
    # Combine all figures
    all_figures = {
        **{f"retrieval_{k}": v for k, v in retrieval_figures.items()},
        **{f"assessment_{k}": v for k, v in assessment_figures.items()},
        **{f"ablation_{k}": v for k, v in ablation_figures.items()}
    }
    
    # Create HTML with all figures
    html_parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "    <title>RAG Assessment Evaluation Report</title>",
        "    <style>",
        "        body { font-family: Arial, sans-serif; margin: 20px; }",
        "        h1 { color: #2c3e50; }",
        "        h2 { color: #3498db; margin-top: 30px; }",
        "        .section { margin-bottom: 40px; }",
        "        .figure-container { margin-bottom: 30px; }",
        "    </style>",
        "</head>",
        "<body>",
        "    <h1>RAG Assessment Evaluation Report</h1>"
    ]
    
    # 1. Retrieval Section
    html_parts.extend([
        "    <div class='section'>",
        "        <h2>1. Retrieval Quality Evaluation</h2>"
    ])
    
    # Add retrieval summary metrics
    retrieval_summary = results.get("retrieval", {}).get("summary", {})
    if retrieval_summary:
        html_parts.extend([
            "        <div class='summary'>",
            "            <h3>Summary Metrics</h3>",
            "            <ul>",
            f"                <li><strong>Average Relevance:</strong> {retrieval_summary.get('avg_relevance', 0):.3f}</li>",
            f"                <li><strong>Average Information Density:</strong> {retrieval_summary.get('avg_info_density', 0):.3f}</li>",
            f"                <li><strong>Average Sources per Unit:</strong> {retrieval_summary.get('avg_source_count', 0):.1f}</li>",
            f"                <li><strong>Average Source Length:</strong> {retrieval_summary.get('avg_source_length', 0):.0f} characters</li>",
            f"                <li><strong>Learning Units Evaluated:</strong> {retrieval_summary.get('total_learning_units_evaluated', 0)}</li>",
            "            </ul>",
            "        </div>"
        ])
    
    # Add retrieval figures
    for name, fig in retrieval_figures.items():
        fig_html = fig.to_html(include_plotlyjs="cdn", full_html=False)
        html_parts.extend([
            f"        <div class='figure-container' id='fig-retrieval-{name}'>",
            f"            <h3>{name.replace('_', ' ').title()}</h3>",
            f"            {fig_html}",
            "        </div>"
        ])
    
    html_parts.append("    </div>")
    
    # 2. Assessment Section
    html_parts.extend([
        "    <div class='section'>",
        "        <h2>2. Educational Assessment Quality</h2>"
    ])
    
    # Add assessment summary metrics
    assessment_summary = results.get("assessment", {}).get("summary", {})
    if assessment_summary:
        html_parts.extend([
            "        <div class='summary'>",
            "            <h3>Summary Metrics</h3>",
            "            <ul>",
            f"                <li><strong>Total Questions:</strong> {assessment_summary.get('total_questions', 0)}</li>",
            f"                <li><strong>Learning Units with Questions:</strong> {assessment_summary.get('total_learning_units_with_questions', 0)}</li>",
            f"                <li><strong>Average Questions per Unit:</strong> {assessment_summary.get('avg_questions_per_unit', 0):.1f}</li>",
            f"                <li><strong>Average Question Length:</strong> {assessment_summary.get('avg_question_length', 0):.0f} characters</li>",
            "            </ul>",
            "        </div>"
        ])
    
    # Add assessment figures
    for name, fig in assessment_figures.items():
        fig_html = fig.to_html(include_plotlyjs="cdn", full_html=False)
        html_parts.extend([
            f"        <div class='figure-container' id='fig-assessment-{name}'>",
            f"            <h3>{name.replace('_', ' ').title()}</h3>",
            f"            {fig_html}",
            "        </div>"
        ])
    
    html_parts.append("    </div>")
    
    # 3. Ablation Study Section
    html_parts.extend([
        "    <div class='section'>",
        "        <h2>3. Ablation Study Results</h2>",
    ])
    
    # Add ablation figures
    for name, fig in ablation_figures.items():
        fig_html = fig.to_html(include_plotlyjs="cdn", full_html=False)
        html_parts.extend([
            f"        <div class='figure-container' id='fig-ablation-{name}'>",
            f"            <h3>{name.replace('_', ' ').title()}</h3>",
            f"            {fig_html}",
            "        </div>"
        ])
    
    html_parts.append("    </div>")
    
    # Close HTML
    html_parts.extend([
        "</body>",
        "</html>"
    ])
    
    # Write HTML to file
    with open(output_file, "w") as f:
        f.write("\n".join(html_parts))
    
    print(f"Evaluation report saved to {output_file}")
    return output_file

def display_streamlit_dashboard(results: Dict[str, Any]):
    """Display interactive evaluation results in Streamlit."""
    st.title("RAG Assessment Evaluation Dashboard")
    
    # Create tabs for different evaluation aspects
    tabs = st.tabs(["Retrieval Quality", "Assessment Quality", "Ablation Study"])
    
    # 1. Retrieval Quality Tab
    with tabs[0]:
        st.header("Retrieval Quality Evaluation")
        
        retrieval_summary = results.get("retrieval", {}).get("summary", {})
        if retrieval_summary:
            st.subheader("Summary Metrics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Average Relevance", f"{retrieval_summary.get('avg_relevance', 0):.3f}")
                st.metric("Average Sources per Unit", f"{retrieval_summary.get('avg_source_count', 0):.1f}")
            with col2:
                st.metric("Average Info Density", f"{retrieval_summary.get('avg_info_density', 0):.3f}")
                st.metric("Learning Units Evaluated", f"{retrieval_summary.get('total_learning_units_evaluated', 0)}")
        
        # Display retrieval figures
        retrieval_figures = create_retrieval_visualizations(results.get("retrieval", {}))
        for name, fig in retrieval_figures.items():
            st.subheader(name.replace('_', ' ').title())
            st.plotly_chart(fig, use_container_width=True)
            
        # Show detailed unit results if available
        learning_units = results.get("retrieval", {}).get("learning_units", {})
        if learning_units:
            st.subheader("Learning Unit Details")
            selected_unit = st.selectbox(
                "Select Learning Unit", 
                options=list(learning_units.keys())
            )
            
            if selected_unit and selected_unit in learning_units:
                unit_data = learning_units[selected_unit]
                st.json(unit_data)
    
    # 2. Assessment Quality Tab
    with tabs[1]:
        st.header("Educational Assessment Quality")
        
        assessment_summary = results.get("assessment", {}).get("summary", {})
        if assessment_summary:
            st.subheader("Summary Metrics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Questions", f"{assessment_summary.get('total_questions', 0)}")
                st.metric("Avg Questions per Unit", f"{assessment_summary.get('avg_questions_per_unit', 0):.1f}")
            with col2:
                st.metric("Units with Questions", f"{assessment_summary.get('total_learning_units_with_questions', 0)}")
                st.metric("Avg Question Length", f"{assessment_summary.get('avg_question_length', 0):.0f}")
        
        # Display assessment figures
        assessment_figures = create_assessment_visualizations(results.get("assessment", {}))
        for name, fig in assessment_figures.items():
            st.subheader(name.replace('_', ' ').title())
            st.plotly_chart(fig, use_container_width=True)
    
    # 3. Ablation Study Tab
    with tabs[2]:
        st.header("Ablation Study Results")
        
        # Display ablation figures
        ablation_figures = create_ablation_visualizations(results.get("ablation", {}))
        for name, fig in ablation_figures.items():
            st.subheader(name.replace('_', ' ').title())
            st.plotly_chart(fig, use_container_width=True)
        
        # Show configuration details
        st.subheader("Configuration Details")
        ablation_results = results.get("ablation", {})
        if ablation_results:
            configs = {}
            for config_name, result in ablation_results.items():
                if "config" in result:
                    configs[config_name] = result["config"]
            
            st.json(configs)

if __name__ == "__main__":
    # Example usage with sample data
    import sys
    
    if len(sys.argv) > 1:
        # Load results from file
        with open(sys.argv[1], 'r') as f:
            results = json.load(f)
            
        # Generate report
        output_file = sys.argv[2] if len(sys.argv) > 2 else "evaluation_report.html"
        create_evaluation_report(results, output_file)
    else:
        print("Usage: python visualization.py results.json [output.html]")
        