using System;
using System.IO;
using System.Text;
using System.Reflection;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Runtime.CompilerServices;
using System.Threading.Tasks;

class MCrypt
{
	const int SaltSize = 32; // 256-bit
	const int KeySize = 32;  // AES-256
	const int IvSize = 16;   // AES block size
	const int Iterations = 100_000;

	static Dictionary<string, GlobalConfigurationSettings> Settings = new Dictionary<string, GlobalConfigurationSettings>();

	static int Main (string[] args)
	{
		Settings = ParseCommandLineArguments (args);

		Dbg ("Verifying Arguments...");
		if (!VerifyCommandLineArguments (Settings))
		{
			PrintUsage ();
			return 1;
		}

		Dbg ("Converting Arguments...");
		ECryptMode Mode = GetSetting<ECryptMode> ("Mode");
		string InputPath = GetSetting<string> ("Inbound");
		string OutputPath = GetSetting<string> ("Outbound");
		string Password = GetSetting<string> ("Key");

		try
		{
			if (!O.FileExists ("", InputPath) && !O.IsDirectory (InputPath))
			{
				O.Print ($"The file supplied to --inbound does not exist!\n\t--inbound {InputPath}");
				return 1;
			}

			if (O.FileExists ("", OutputPath))
			{
				O.Print ($"The file supplied to --outbound already exists!\n\t--outbound {OutputPath}");
				return 1;
			}

			switch (Mode)
			{
				case ECryptMode.Encrypt:
					Dbg ("Encrypting...");

					EncryptFile (InputPath, OutputPath, Password);
					Console.WriteLine ("Encrypt complete.");
					break;
				case ECryptMode.Decrypt:
					Dbg ("Decrypting...");

					DecryptFile (InputPath, OutputPath, Password);
					Console.WriteLine ("Decrypt complete.");
					break;
			}
		}
		catch (Exception ex)
		{
			Console.WriteLine ($"Error during {Mode}.\n\t{ex.Message}");
			return 1;
		}

		Dbg ("Terminate with 0.");
		return 0;
	}

	static int EncryptMultiple (string[] InputPaths, string OutputPath, string Password)
	{
		int ReturnCode = 0;
		Parallel.ForEach (InputPaths, (s, State) =>
		{
			O.Print ($"Encrypting {s}...");

			string[] FQFileName = s.Split (Path.DirectorySeparatorChar);
			string FileName = FQFileName[FQFileName.Length - 1];
			ReturnCode = EncryptFile (s, Path.Combine (OutputPath, FileName), Password);

			if (ReturnCode != 0)
			{
				if (!GetSetting<bool> ("Skip"))
				{
					O.Print ($"Error Encrypting {s}!\n--skip not specified. Terminating", ConsoleColor.Red);

					State.Break ();
				}
				else
				{
					O.Print ($"Error Encrypting {s}!\n--skip specified. Skipping", ConsoleColor.Yellow);
				}
			}
		});

		return ReturnCode;
	}

	static int EncryptFile (string InputPath, string OutputPath, string Password)
	{
		Dbg ($"EncryptFile ({InputPath}, {OutputPath}, Password) - Function entry...");
		if (O.IsDirectory (InputPath))
		{
			Dbg ($"EncryptFile ({InputPath}, {OutputPath}, Password) - InputPath is a directory...");
			string[] AllEntriesInDirectory = O.GetAllEntriesInDirectory (InputPath);
			if (!O.IsDirectory (OutputPath) && !O.FileExists (OutputPath, ""))
			{
				Dbg ($"EncryptFile ({InputPath}, {OutputPath}, Password) - Creating directory...");
				Directory.CreateDirectory (OutputPath);
			}
			else
			{
				O.Print ("--outbound already exists or is a file!", ConsoleColor.Red);
				return 1;
			}

			return EncryptMultiple (AllEntriesInDirectory, OutputPath, Password);
		}

		if (InputPath.Contains ("*") || InputPath.Contains ("?"))
		{
			Dbg ($"EncryptFile ({InputPath}, {OutputPath}, Password) - Wildcards found...");
			string[] WildcardEntriesInDirectory = O.GetWildcardEntriesInDirectory (InputPath, InputPath);
			return EncryptMultiple (WildcardEntriesInDirectory, OutputPath, Password);
		}

		Dbg ($"EncryptFile ({InputPath}, {OutputPath}, Password) - Making encryption bits...");
		byte[] Salt = RandomBytes (SaltSize);
		byte[] IV = RandomBytes (IvSize);
		byte[] Derived = DeriveKey (Password, Salt, KeySize * 2);
		byte[] AESKey = new byte[KeySize];
		byte[] HMACKey = new byte[KeySize];
		Array.Copy (Derived, 0, AESKey, 0, KeySize);
		Array.Copy (Derived, KeySize, HMACKey, 0, KeySize);

		Dbg ($"EncryptFile ({InputPath}, {OutputPath}, Password) - AES...");
		using (Aes AES = Aes.Create ())
		{
			AES.Key = AESKey;
			AES.IV = IV;
			AES.Mode = CipherMode.CBC;
			AES.Padding = PaddingMode.PKCS7;

			using (MemoryStream MS = new MemoryStream ())
			{
				using (CryptoStream CryptoStream = new CryptoStream (MS, AES.CreateEncryptor (), CryptoStreamMode.Write))
				using (FileStream FSInput = new FileStream (InputPath, FileMode.Open, FileAccess.Read))
				{
					FSInput.CopyTo (CryptoStream);
				}

				byte[] Ciphertext = MS.ToArray ();
				using (FileStream FSOutput = new FileStream (OutputPath, FileMode.Create, FileAccess.Write))
				{
					FSOutput.Write (Salt, 0, Salt.Length);
					FSOutput.Write (IV, 0, IV.Length);
					FSOutput.Write (Ciphertext, 0, Ciphertext.Length);

					using (HMACSHA256 HMAC = new HMACSHA256 (HMACKey))
					{
						byte[] AuthData = Combine (Salt, IV, Ciphertext);
						byte[] Tag = HMAC.ComputeHash (AuthData);
						FSOutput.Write (Tag, 0, Tag.Length);
					}
				}
			}
		}

		Dbg ($"EncryptFile ({InputPath}, {OutputPath}, Password) - return 0...");
		return 0;
	}

	static int DecryptDirectory (string[] InputPaths, string OutputPath, string Password)
	{
		int ReturnCode = 0;
		Parallel.ForEach (InputPaths, (s, State) =>
		{
			O.Print ($"Decrypting {s}...");

			string[] FQFileName = s.Split (Path.DirectorySeparatorChar);
			if (FQFileName.Length == 0)
			{
				O.Print ($"Error Decrypting {s}!\nInputPath received a path without a parent directory.", ConsoleColor.Red);

				ReturnCode = 1;
				State.Break ();
			}

			string FileName = FQFileName[FQFileName.Length - 1];
			ReturnCode = DecryptFile (s, Path.Combine (OutputPath, FileName), Password);

			if (ReturnCode != 0)
			{
				if (!GetSetting<bool> ("Skip"))
				{
					O.Print ($"Error Decrypting {s}!\n--skip not specified. Terminating", ConsoleColor.Red);

					State.Break ();
				}
				else
				{
					O.Print ($"Error Decrypting {s}!\n--skip specified. Skipping", ConsoleColor.Yellow);
				}
			}
		});

		return ReturnCode;
	}
	
	static int DecryptFile (string InputPath, string OutputPath, string Password)
	{
		if (O.IsDirectory (InputPath))
		{
			string [] AllEntriesInDirectory = O.GetAllEntriesInDirectory (InputPath);

			if (!O.IsDirectory (OutputPath) && !O.FileExists (OutputPath, ""))
			{
				Dbg ($"DecryptFile ({InputPath}, {OutputPath}, Password) - Creating directory...");
				Directory.CreateDirectory (OutputPath);
			}
			else
			{
				O.Print ("--outbound already exists or is a file!", ConsoleColor.Red);
				return 1;
			}

			return DecryptDirectory (AllEntriesInDirectory, OutputPath, Password);
		}

		byte[] FileBytes = File.ReadAllBytes (InputPath);
		if (FileBytes.Length < SaltSize + IvSize + 32)
		{
			O.Print ($"InvalidDataException - File too small to be valid.", ConsoleColor.Red);
			return 1;
		}

		byte[] Salt = new byte[SaltSize];
		byte[] IV = new byte[IvSize];
		byte[] Tag = new byte[32]; // HMAC-SHA256
		int CiphertextLength = FileBytes.Length - SaltSize - IvSize - Tag.Length;
		byte[] Ciphertext = new byte[CiphertextLength];

		Array.Copy (FileBytes, 0, Salt, 0, SaltSize);
		Array.Copy (FileBytes, SaltSize, IV, 0, IvSize);
		Array.Copy (FileBytes, SaltSize + IvSize, Ciphertext, 0, CiphertextLength);
		Array.Copy (FileBytes, SaltSize + IvSize + CiphertextLength, Tag, 0, Tag.Length);

		byte[] Derived = DeriveKey (Password, Salt, KeySize * 2);
		byte[] AESKey = new byte[KeySize];
		byte[] HMACKey = new byte[KeySize];
		Array.Copy (Derived, 0, AESKey, 0, KeySize);
		Array.Copy (Derived, KeySize, HMACKey, 0, KeySize);

		using (HMACSHA256 HMAC = new HMACSHA256 (HMACKey))
		{
			byte[] AuthData = Combine (Salt, IV, Ciphertext);
			byte[] ComputedTag = HMAC.ComputeHash (AuthData);
			if (!Compare (Tag, ComputedTag))
			{
				Dbg ("CryptographicException - HMAC verification failed. The file may be corrupted or the password is incorrect.");
				O.Print ("Wrong password!", ConsoleColor.Magenta);
				return 1;
			}
		}

		using (Aes AES = Aes.Create ())
		{
			AES.Key = AESKey;
			AES.IV = IV;
			AES.Mode = CipherMode.CBC;
			AES.Padding = PaddingMode.PKCS7;

			using (MemoryStream MS = new MemoryStream (Ciphertext))
			using (CryptoStream CryptoStream = new CryptoStream (MS, AES.CreateDecryptor (), CryptoStreamMode.Read))
			using (FileStream FSOutput = new FileStream (OutputPath, FileMode.Create, FileAccess.Write))
			{
				CryptoStream.CopyTo (FSOutput);
			}
		}

		return 0;
	}

	static byte[] DeriveKey (string Password, byte[] Salt, int Length)
	{
		using (Rfc2898DeriveBytes KDF = new Rfc2898DeriveBytes (Password, Salt, Iterations, HashAlgorithmName.SHA256))
		{
			return KDF.GetBytes (Length);
		}
	}

	static byte[] RandomBytes (int size)
	{
		byte[] Bytes = new byte[size];
		using (RandomNumberGenerator RNG = RandomNumberGenerator.Create ())
		{
			RNG.GetBytes (Bytes);
		}
		return Bytes;
	}

	static byte[] Combine (params byte[][] Arrays)
	{
		int Length = 0;
		foreach (byte[] A in Arrays)
			Length += A.Length;

		byte[] Result = new byte[Length];
		int Offset = 0;
		foreach (byte[] A in Arrays)
		{
			Buffer.BlockCopy (A, 0, Result, Offset, A.Length);
			Offset += A.Length;
		}
		return Result;
	}

	static bool Compare (byte[] A, byte[] B)
	{
		if (A.Length != B.Length)
			return false;

		int Diff = 0;
		for (int i = 0; i < A.Length; i++)
			Diff |= A[i] ^ B[i];

		return Diff == 0;
	}


	static Dictionary<string, GlobalConfigurationSettings> ParseCommandLineArguments(params string[] ArgV)
	{
		Dictionary<string, GlobalConfigurationSettings> UserProvidedConfiguration = new Dictionary<string, GlobalConfigurationSettings>();

		int Iterator = 0;
		int ArgC = ArgV.Length;
		while (Iterator < ArgC)
		{
			switch (ArgV[Iterator])
			{
				case "--encrypt":
					Dbg ("Processing --encrypt");
					Iterator += 1;

					Upsert (ref UserProvidedConfiguration, "Mode", new GlobalConfigurationSettings (ECryptMode.Encrypt));
					break;

				case "--decrypt":
					Dbg ("Processing --decrypt");
					Iterator += 1;

					Upsert (ref UserProvidedConfiguration, "Mode", new GlobalConfigurationSettings (ECryptMode.Decrypt));
					break;

				case "--inbound":
					Dbg ("Processing --inbound");
					Iterator += 1;

					if (!(Iterator < ArgC))
					{
						O.Print ("Option --inbound requires one argument!", ConsoleColor.Red);
						break;
					}

					if (!O.FileExists ("", ArgV[Iterator]) && !O.IsDirectory (ArgV[Iterator]))
					{
						O.Print ($"The value given to option --inbound ({ArgV[Iterator]}) does not exist either as a file or a directory!", ConsoleColor.Red);
						break;
					}

					Upsert (ref UserProvidedConfiguration, "Inbound", new GlobalConfigurationSettings (ArgV[Iterator]));

					Iterator += 1;
					break;

				case "--outbound":
					Dbg ("Processing --outbound");
					Iterator += 1;

					if (!(Iterator < ArgC))
					{
						O.Print ("Option --outbound requires one argument!", ConsoleColor.Red);
						break;
					}

					Upsert (ref UserProvidedConfiguration, "Outbound", new GlobalConfigurationSettings (ArgV[Iterator]));

					Iterator += 1;
					break;

				case "--key":
					Dbg ("Processing --key");
					Iterator += 1;

					if (!(Iterator < ArgC))
					{
						O.Print ("Option --key requires one argument!", ConsoleColor.Red);
						break;
					}

					if (O.FileExists ("", ArgV[Iterator]))
					{
						break;
					}

					Upsert (ref UserProvidedConfiguration, "Key", new GlobalConfigurationSettings (ArgV[Iterator]));

					Iterator += 1;
					break;

				case "--debug":
					Upsert (ref UserProvidedConfiguration, "Debug", new GlobalConfigurationSettings (true));

					Settings = UserProvidedConfiguration;
					Dbg ("--debug flag set");

					Iterator += 1;
					break;

				case "--skip":
					Dbg ("Processing --skip");
					Upsert (ref UserProvidedConfiguration, "Skip", new GlobalConfigurationSettings (true));

					Iterator += 1;
					break;

				case  "__HELP__":
				case "?":
				case "--help":
					Upsert (ref UserProvidedConfiguration, "Help", new GlobalConfigurationSettings (true));
					return UserProvidedConfiguration;

			}
		}

		if (!UserProvidedConfiguration.ContainsKey ("Outbound"))
		{
			Dbg ("No --outbound set. Defaulting...");
			string RequestedOperation = UserProvidedConfiguration.ContainsKey ("Mode")
				? UserProvidedConfiguration["Mode"].GetValue<ECryptMode> () == ECryptMode.Encrypt
					? "encrypted"
					: "decrypted"
				: "MCRYPT";

			string InboundParam = UserProvidedConfiguration.ContainsKey ("Inbound")
				? $"{UserProvidedConfiguration["Inbound"].GetValue<string> ()}.{RequestedOperation}"
				: "OutResult";

			string[] NameSplit = InboundParam.Split (Path.DirectorySeparatorChar);
			string FileNamePart = (NameSplit.Length == 0)
				? NameSplit[0]
				: NameSplit[NameSplit.Length - 1];

			string PWD = Directory.GetCurrentDirectory ();
			string DefaultOutbound = $"{PWD}{Path.DirectorySeparatorChar}{FileNamePart}";

			Dbg ($"--outbound Defaulted. RequestedOperation: {RequestedOperation} | DefaultOutbound: {DefaultOutbound}");
			Upsert (ref UserProvidedConfiguration, "Outbound", new GlobalConfigurationSettings (DefaultOutbound));
		}

		Dbg ("ParseCommandLineArguments () Complete.");
		return UserProvidedConfiguration;
	}

	static void Upsert(ref Dictionary<string, GlobalConfigurationSettings> UserProvidedConfiguration, string Option, GlobalConfigurationSettings Value)
	{
		if (UserProvidedConfiguration.ContainsKey (Option))
			UserProvidedConfiguration[Option] = Value;
		else
			UserProvidedConfiguration.Add (Option, Value);
	}

	[MethodImpl(MethodImplOptions.AggressiveInlining)]
	static bool VerifyCommandLineArguments (Dictionary<string, GlobalConfigurationSettings> Check)
	{
		if (Check.ContainsKey ("Help"))
			return false;

		EValidation Validation = EValidation.None;
		if (!Check.ContainsKey ("Mode"))
			Validation |= EValidation.Mode;
		if (!Check.ContainsKey ("Inbound"))
			Validation |= EValidation.Inbound;
		if (!Check.ContainsKey ("Key"))
			Validation |= EValidation.Key;

		if ((int)(Validation & EValidation.Mode) > 0)
			O.Print ("Missing Mode");
		if ((int)(Validation & EValidation.Inbound) > 0)
			O.Print ("Missing Inbound");
		if ((int)(Validation & EValidation.Key) > 0)
			O.Print ("Missing Key");

		return Validation == EValidation.None;
	}

	static void PrintUsage ()
	{
		StringBuilder SB = new StringBuilder ();
		SB.AppendLine ();
		SB.Append ("mcrypt (--encrypt|--decrypt) --inbound FILE|DIRECTORY [--outbound FILE|DIRECTORY] --key KEY [--skip]");
		SB.AppendLine ();
		O.Print (SB.ToString ());
	}

	static void Dbg (string Message, ConsoleColor FColour = ConsoleColor.Cyan, ConsoleColor BColour = ConsoleColor.Black, bool bRetrievePrimitively = false)
	{
		if (!bRetrievePrimitively)
		{
			if (GetSetting<bool> ("Debug"))
				O.Print ($"DEBUG - {Message}", FColour, BColour);
		}
		else
		{
			if (Settings.ContainsKey ("Debug"))
				O.Print ($"DEBUG - {Message}", FColour, BColour);
		}
	}

	static T GetSetting<T> (string Key)
	{
		if (Settings.ContainsKey (Key))
			return Settings[Key].GetValue<T> ();

		Dbg ($"Defaulting {Key}", bRetrievePrimitively: true);
		return default (T);
	}
}

enum EValidation : int
{
	None = 0,
	Mode = 1,
	Inbound = 2,
	Key = 4,
	HelpRequested = 8
}

enum ECryptMode
{
	None,
	Encrypt,
	Decrypt
}

public struct GlobalConfigurationSettings
{
	public Type T;
	public object Value;

	public GlobalConfigurationSettings (object Value) : this ()
	{
		this.Value = Value;
		T = Value.GetType ();
	}

	[MethodImpl(MethodImplOptions.AggressiveInlining)]
	public R GetValue<R>()
	{
		if (Value.TryCast<R> (out R Casted))
			return Casted;
		return default (R);
	}
}

public static class ObjectExtensions
{
	[MethodImpl(MethodImplOptions.AggressiveInlining)]
	public static bool Is<T>(this object O) => O is T || O.GetType() == typeof(T);

	[MethodImpl(MethodImplOptions.AggressiveInlining)]
	public static bool Is<T>(this object O, out T Casted)
	{
		Casted = O.Cast<T>();
		return Casted != null;
	}

	[MethodImpl(MethodImplOptions.AggressiveInlining)]
	public static bool TryCast<T>(this object O, out T Casted) => O.Is<T>(out Casted);

	[MethodImpl(MethodImplOptions.AggressiveInlining)]
	public static object Cast(this object O, Type Type) => Convert.ChangeType(O, Type);

	[MethodImpl(MethodImplOptions.AggressiveInlining)]
	public static T Cast<T>(this object O)
	{
		return O is T R
			? R
			: (T)Convert.ChangeType(O, typeof(T));
	}
}

public static class O
{
	public static void Print (string Content, ConsoleColor FColour = ConsoleColor.Gray, ConsoleColor BColour = ConsoleColor.Black)
	{
		SetColours (FColour, BColour);
		Console.WriteLine (Content);
		ResetColours ();
	}

	public static void SetColours (ConsoleColor FColour, ConsoleColor BColour = ConsoleColor.Black)
	{
		Console.ForegroundColor = FColour;
		Console.BackgroundColor = BColour;
	}

	public static void ResetColours()
	{
		SetColours (ConsoleColor.Gray);
	}

	[MethodImpl (MethodImplOptions.AggressiveInlining)]
	public static bool FileExists (string Path, string NameOfFile)
	{
		return File.Exists (System.IO.Path.Combine (Path, NameOfFile));
	}

	[MethodImpl (MethodImplOptions.AggressiveInlining)]
	public static bool IsDirectory (string Path)
	{
		return Directory.Exists (Path);
	}

	[MethodImpl(MethodImplOptions.AggressiveInlining)]
	public static string[] GetAllEntriesInDirectory (string FQPath, EDirectorySortOrder DirectorySortOrder = EDirectorySortOrder.Name)
	{
		return Directory.GetFiles (FQPath);
	}

	[MethodImpl(MethodImplOptions.AggressiveInlining)]
	public static string[] GetWildcardEntriesInDirectory (string FQPath, string WildcardExpression, EDirectorySortOrder DirectorySortOrder = EDirectorySortOrder.Name)
	{
		return Directory.GetFiles (FQPath, WildcardExpression);
	}

}

public enum EWriteMode
{
	Append,
	Overwrite
}

public enum EDirectorySortOrder
{
	Default = 0,
	Ascending = 1,
	Descending = 2,
	Name = 4,
	LastWriteTime = 8,
}
