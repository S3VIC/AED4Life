using System.Text.Json.Serialization;

namespace AED4Life.DataModel.Enums;

[JsonConverter(typeof(JsonStringEnumConverter<ReportStatus>))]
public enum ReportStatus {
	Submitted = 0,
	UnderReview = 1,
	Confirmed = 2,
	Rejected = 3
}
