using System.Text.Json.Serialization;

namespace AED4Life.Requests;

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public sealed record CreateAEDReportRequest(
	Int64? UserId, Int64? AEDId, String? PhotoUrl, String? Description,
	Int32? AvailabilityStartHour, Int32? AvailabilityEndHour, Boolean? IsPubliclyAccessible, Int32? Rating);
