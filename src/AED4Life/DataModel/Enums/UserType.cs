using System.Text.Json.Serialization;

namespace AED4Life.DataModel.Enums;

[JsonConverter(typeof(JsonStringEnumConverter<UserType>))]
public enum UserType {
	Admin = 0,
	Normal = 1,
	PublicRepresentative = 2,
	Maintainer = 3
}
