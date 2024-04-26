using System;

public class Entry
{
	static int Main(string[] Args)
	{
		Random R = new Random();

		int Code = R.Next(0, 99999);
		string Formatted = Code.ToString("D5");
		string ForceCode = Args.Length > 0
			? Args[0]
			: Formatted;

		bool bUseSourceSisId = Args.Length > 1
			? Args[1] != "__NO_SOURCE__"
			: true;

		string SourceSisId = bUseSourceSisId
			? $",\"source_sis_id\": \"{ForceCode}_U_2023_SPR\""
			: string.Empty;

#if WITH_DEBUG
		foreach (string s in Args)
			Console.WriteLine(s);

		Console.WriteLine(bUseSourceSisId);
		Console.WriteLine(SourceSisId);
#endif // WITH_DEBUG
		
		string RetVal = $"{{\"course_sis_id\": \"{Formatted}_U_2024_AUT\",\"name\": \"{ForceCode} Introduction to Leganto Automation\",\"faculty\": \"FEIT\",\"start_date\": \"2024-02-28\",\"end_date\": \"2025-02-28\",\"year\": \"2024\",\"instructors\": [\"Instructor1\",\"Instructor2\"],\"study_package_codes\": [\"StudyPackageCodes\"]{SourceSisId}}}";

		Console.WriteLine(RetVal);
		
		return 0;
	}
}
