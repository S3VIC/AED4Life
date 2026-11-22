using AED4Life.DataModel.Enums;

namespace AED4Life.DataModel.DTOs;

public sealed record AEDReportResponse(
	Int64 Id, Int64 UserId, Int64? AEDId, String PhotoUrl,
	DateTime Created, DateTime LastUpdated, ReportStatus Status);
