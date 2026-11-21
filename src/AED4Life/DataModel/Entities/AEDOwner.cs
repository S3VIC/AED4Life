namespace AED4Life.DataModel.Entities;

public class AEDOwner {
	public Int64 RegonNumber { get; set; }
	
	public Boolean IsPublic { get; set; }
	
	public required String Name { get; set; }
	
	public Int64 CityId { get; set; }
	
	public Int64 StreetId { get; set; }
}