using System.Text.Json.Serialization;
using AED4Life.DataModel.Enums;

namespace AED4Life.DataModel.Entities;

public class User {
	public Int64 Id { get; set; }
	public required String Username { get; set; }
	[JsonIgnore]
	public String PasswordHash { get; set; } = String.Empty;
	public required String FirstName { get; set; }
	public required String LastName { get; set; }
	public DateOnly BirthDate { get; set; }
	public Int64 AddressId { get; set; }
	public UserType Type { get; set; } = UserType.Normal;
}
