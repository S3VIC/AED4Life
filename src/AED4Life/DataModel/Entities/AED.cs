using AED4Life.DataModel.Enums;

namespace AED4Life.DataModel.Entities;

public class AED {
	public Int64 Id { get; set; }
	public Int64? AddressId { get; set; }
	public Int64? OwnerId { get; set; }
	public DateTime Created { get; set; }
	public DateTime LastUpdated { get; set; }
	public String? SerialNumber { get; set; }
	public Double? Latitude { get; set; }
	public Double? Longitude { get; set; }
	public AEDAccess? Access { get; set; }
	public Int32? AvailabilityStartHour { get; set; }
	public Int32? AvailabilityEndHour { get; set; }
	public AEDRating? Rating { get; set; }
}