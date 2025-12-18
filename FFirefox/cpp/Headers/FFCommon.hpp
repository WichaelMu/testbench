#pragma once
#include <string>

namespace FFCommon
{
	// Paths / logging
	std::string GetDataRoot();
	std::string JoinPath(const std::string& A, const std::string& B);
	void        EnsureDataRoot();
	void        Log(const std::string& Component, const std::string& Message);

	// Watcher / Tracker integration
	bool LoadFocusWatcherState(std::string& OutApp, int& OutPid, std::string& OutProfileName, std::string& OutProfilePath, std::string& OutReason);
	void RememberProfileFromWatcher(const std::string& ProfileName, const std::string& ProfilePath);
	bool GetLatestProfileFromWatcher(std::string& OutProfileName, std::string& OutProfilePath);

	// Firefox profiles (profiles.ini)
	bool IsProfileValid(const std::string& ProfileName, const std::string& ProfilePath);
	bool MapProfileNameToPath(const std::string& ProfileName, std::string& OutPath);
	bool GetDefaultProfile(std::string& OutProfileName, std::string& OutProfilePath);

	// Fallback when watcher/tracker give nothing
	bool ChooseProfileBySystemHeuristics(std::string& OutProfileName, std::string& OutProfilePath, std::string& OutReason);

	// Routing helper
	void ExplainSelection(const std::string& Where, const std::string& Reason, const std::string& Name, const std::string& Path);
}
