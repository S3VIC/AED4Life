using AED4Life.DataModel.Enums;

namespace AED4Life.DataModel.Entities;

public class AEDReport {
	public Int64 Id { get; set; }
	public Int64 UserId { get; set; }
	public Int64? AEDId { get; set; }
	public required String PhotoUrl { get; set; }
	public DateTime Created { get; set; }
	public DateTime LastUpdated { get; set; }
	public ReportStatus Status { get; set; } = ReportStatus.Submitted;
}
