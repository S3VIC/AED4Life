namespace AED4Life.DataModel.Entities;

public class AED {
	public Int64 Id { get; set; }
	public Int64 CityId { get; set; }
	public Int64 StreetId { get; set; }
	public Int32 HouseNumber { get; set; }
	public DateTime Created { get; set; }
	public DateTime LastUpdated { get; set; }
	public required String SerialNumber { get; set; }
}