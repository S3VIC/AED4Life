namespace AED4Life.DataModel.DTOs;

public sealed record AEDValidationIssue(Int64 Id, String[] Missing);

/// <summary>
/// Result of a validation run. Missing counts AEDs per missing data group (location, address, name, access, hours);
/// an AED missing several groups is counted in each. Issues lists at most the first 100 invalid AEDs by ID.
/// </summary>
public sealed record AEDValidationResponse(
	Boolean DryRun, Int32 Checked, Int32 Valid, Int32 MissingData, Int32 Changed,
	Dictionary<String, Int32> Missing, List<AEDValidationIssue> Issues);
