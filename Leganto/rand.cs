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

		if (!int.TryParse(ForceCode, out _))
			ForceCode = Formatted;

		Settings Settings = new Settings();
		Settings.SetDefaults();
		ProcessArguments(Args, ref Settings);

		string SourceSisId = Settings.bUseSourceSisId
			? $",\"source_sis_id\": \"{ForceCode}_U_2023_SPR\""
			: string.Empty;

		string Prefix = Settings.bUseMPrefix
			? "M"
			: string.Empty;

		string SubjectId = Settings.bUseCustomSubjectId
			? GetParameterAfterOption(Args, "__CUSTOM_SUBJECT_ID__", ForceCode)
			: ForceCode;

#if WITH_DEBUG
		foreach (string s in Args)
			Console.WriteLine(s);

		Console.WriteLine(Settings.bUseSourceSisId);
		Console.WriteLine(SourceSisId);
#endif // WITH_DEBUG
		
		string RetVal = $"{{\"course_sis_id\": \"{Prefix}{Formatted}_U_2024_AUT\",\"name\": \"{SubjectId} Introduction to Leganto Automation - MW\",\"faculty\": \"FEIT\",\"start_date\": \"2024-02-28\",\"end_date\": \"2025-02-28\",\"year\": \"2024\",\"instructors\": [\"Instructor1\",\"Instructor2\"],\"study_package_codes\": [\"StudyPackageCodes\"]{SourceSisId}}}";

		Console.WriteLine(RetVal);
		
		return 0;
	}

	static void ProcessArguments(string[] Args, ref Settings Settings) {
		foreach (string V in Args)
		{
			switch (V)
			{
				case "__NO_SOURCE__":
					Settings.bUseSourceSisId = false;
					break;
				case "__WITH_PREFIX__":
					Settings.bUseMPrefix = true;
					break;
				case "__CUSTOM_SUBJECT_ID__":
					Settings.bUseCustomSubjectId = true;
					break;
			}
		}
	}

	static string GetParameterAfterOption(string[] Args, string Option, string Default)
	{
		for (int i = 0; i < Args.Length - 1; ++i)
			if (Args[i] == Option)
				return Args[i + 1];
		return Default;
	}

}

struct Settings {
	public bool bUseSourceSisId;
	public bool bUseMPrefix;
	public bool bUseCustomSubjectId;

	public void SetDefaults() {
		bUseSourceSisId = true;
		bUseMPrefix = false;
		bUseCustomSubjectId = false;
	}
}
