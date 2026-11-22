namespace AED4Life.DataModel.Entities;

public class Address {
	public Int64 Id { get; set; }
	public Int64 StreetId { get; set; }
	public Int64 CityId { get; set; }
	public Int32 PostalCodeId { get; set; }
	public Int32 BuildingNumber { get; set; }
}
