using System;
using System.Text;
using System.Globalization;

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

		DateTime Now = DateTime.Now;
		string TimeNow = Now.ToString(new CultureInfo("en-AU"));

		if (!int.TryParse(ForceCode, out _))
			ForceCode = Formatted;

		Settings Settings = new Settings();
		Settings.SetDefaults();
		ProcessArguments(Args, ref Settings);

		foreach (string V in Args)
			if (V == "__HELP__" || V == "?")
				return 0;

		string SourceSisId = Settings.bUseSourceSisId
			? Settings.bUseGeneratedSource
				? $",\"source_sis_id\": \"{Formatted}_U_2023_SPR\""
				: $",\"source_sis_id\": \"{ForceCode}_U_2023_SPR\""
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
		
		string RetVal = $"{{\"course_sis_id\": \"{Prefix}{Formatted}_U_2024_AUT\",\"name\": \"{ForceCode} Leganto Automation - {TimeNow} - MW\",\"faculty\": \"FEIT\",\"start_date\": \"2024-02-28\",\"end_date\": \"2025-02-28\",\"year\": \"2024\",\"instructors\": [\"Instructor1\",\"Instructor2\"],\"study_package_codes\": [\"{SubjectId}\"]{SourceSisId}}}";

		Console.WriteLine(RetVal);
		
		return 0;
	}

	static void Help() {
		string[] InternallyDefinedCommands = new string[]
		{
			"__NO_SOURCE__ - Omits 'source_sis_id'.",
			"__RAND_SOURCE__ - Force 'source_sis_id' to use the randomly gen'd value, but keep the custom code in the `name`.",
			"__WITH_PREFIX__ - Use an M prefix in `course_sis_id`.",
			"__CUSTOM_SUBJECT_ID__ - Uses a custom Subject ID in `name`."
		};

		StringBuilder SB = new StringBuilder();
		foreach (string IDC in InternallyDefinedCommands)
			SB.AppendLine($"\t{IDC}\n");
		Console.WriteLine(SB.ToString());
	}

	static void ProcessArguments(string[] Args, ref Settings Settings) {
		foreach (string V in Args)
		{
			switch (V)
			{
				case "__NO_SOURCE__":
					Settings.bUseSourceSisId = false;
					break;
				case "__RAND_SOURCE__":
					Settings.bUseGeneratedSource = true;
					break;
				case "__WITH_PREFIX__":
					Settings.bUseMPrefix = true;
					break;
				case "__CUSTOM_SUBJECT_ID__":
					Settings.bUseCustomSubjectId = true;
					break;
				case "__HELP__":
				case "?":
					Help();
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
	public bool bUseGeneratedSource;
	public bool bUseMPrefix;
	public bool bUseCustomSubjectId;

	public void SetDefaults() {
		bUseSourceSisId = true;
		bUseGeneratedSource = false;
		bUseMPrefix = false;
		bUseCustomSubjectId = false;
	}
}
