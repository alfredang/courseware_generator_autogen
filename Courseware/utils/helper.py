import pandas as pd


def retrieve_excel_data(context: dict, sfw_dataset_dir: str) -> dict:
    # Load the Excel file
    excel_data = pd.ExcelFile(sfw_dataset_dir)
    
    # Load the specific sheet named 'TSC_K&A'
    df = excel_data.parse('TSC_K&A')
    
    tsc_code = context.get("TSC_Code")
    # Filter the DataFrame based on the TSC Code
    filtered_df = df[df['TSC Code'] == tsc_code]
    
    if not filtered_df.empty:
        row = filtered_df.iloc[0]
        
        context["TSC_Sector"] = str(row['Sector'])
        context["TSC_Sector_Abbr"] = str(tsc_code.split('-')[0])
        context["TSC_Category"] = str(row['Category'])
        context["Proficiency_Level"] = str(row['Proficiency Level'])
        context["Proficiency_Description"] = str(row['Proficiency Description'])

    # Return the retrieved data as a dictionary
    return context
