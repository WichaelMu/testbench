#!/usr/bin/env python3.10

import pandas as pd

# Load the two CSV files into Pandas dataframes
df1 = pd.read_csv ('d1.csv', encoding='utf-16')
df2 = pd.read_csv ('d2.csv', encoding='uts-16')

# Ensure the columns are in the same order for comparison
df1 = df1[df2.columns]

# Find rows which are different between the two dataframes
diff_df = pd.concat ([df1,df2]).drop_duplicates (keep = "first")

# Identify rows from df1 not in df2 (removed or changed)
removed_or_changed = pd.merge (df1, diff_df, how = 'inner')

# Identify rows from df2 not in df1 (added or changed)
added_or_changed = pd.merge (df2, diff_df, how = 'inner')

# Mark the changes for clarity
removed_or_changed['Status'] = 'Removed or Changed'
added_or_changed['Status'] = 'Added or Changed'

# Combine the results to get a comprehensive diff dataframe
diff_result = pd.concat ([removed_or_changed, added_or_changed], ignore_index = True)

# Optional: Save the diff result to a new CSV file
diff_result.to_csv ('diff-result.csv', index = False)

print (diff_result)
